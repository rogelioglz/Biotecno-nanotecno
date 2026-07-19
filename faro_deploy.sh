#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 -a APP_NAME [-e ENV] [--host FARO_HOST] [--token FARO_TOKEN]

Genera un paquete de despliegue para el proyecto detectado y lo sube a Faro.

Environment variables:
  FARO_HOST   Optional. Host URL of Faro (e.g. https://faro.example.com)
  FARO_TOKEN  Optional. API token for Faro.

Options:
  -a APP_NAME  (required) Nombre de la aplicación en Faro
  -e ENV       Entorno objetivo (default: staging)
  --help       Muestra esta ayuda

Example:
  FARO_HOST=https://faro.example.com FARO_TOKEN=xxx ./faro_deploy.sh -a mi-app -e production
EOF
}

APP_NAME=""
ENVIRONMENT="staging"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -a) APP_NAME="$2"; shift 2;;
    -e) ENVIRONMENT="$2"; shift 2;;
    --host) FARO_HOST="$2"; shift 2;;
    --token) FARO_TOKEN="$2"; shift 2;;
    --help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

if [[ -z "$APP_NAME" ]]; then
  echo "Error: -a APP_NAME is required"
  usage
  exit 1
fi

OUT_DIR=".faro_build"
OUT_TAR="${APP_NAME}-${ENVIRONMENT}-deploy.tar.gz"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

echo "Detectando tipo de proyecto..."
PROJECT_TYPE="unknown"
if [[ -f package.json ]]; then
  PROJECT_TYPE="node"
elif [[ -f go.mod ]]; then
  PROJECT_TYPE="go"
elif [[ -f pyproject.toml ]] || [[ -f requirements.txt ]] || [[ -d tests ]]; then
  PROJECT_TYPE="python"
elif [[ -f Cargo.toml ]]; then
  PROJECT_TYPE="rust"
elif [[ -f Makefile ]]; then
  PROJECT_TYPE="make"
fi

echo "Proyecto detectado: $PROJECT_TYPE"

case "$PROJECT_TYPE" in
  node)
    echo "Instalando dependencias npm..."
    if command -v npm >/dev/null 2>&1; then
      npm ci --no-audit --no-fund || npm install --no-audit --no-fund
    else
      echo "npm no está disponible en PATH"; exit 1
    fi
    if jq -e '.scripts.build' package.json >/dev/null 2>&1; then
      echo "Ejecutando 'npm run build'..."
      npm run build
    fi
    # Empaqueta dist / build outputs si existen
    if [[ -d dist ]]; then cp -r dist "$OUT_DIR/"; fi
    if [[ -d build ]]; then cp -r build "$OUT_DIR/"; fi
    ;;

  go)
    echo "Compilando Go..."
    if command -v go >/dev/null 2>&1; then
      mkdir -p "$OUT_DIR/bin"
      go build -o "$OUT_DIR/bin/$(basename "$APP_NAME")" ./...
    else
      echo "go no está disponible en PATH"; exit 1
    fi
    ;;

  python)
    echo "Preparando artefactos Python..."
    mkdir -p "$OUT_DIR/python"
    # Intentar crear wheel si hay setup.py/pyproject
    if command -v python3 >/dev/null 2>&1; then
      if [[ -f pyproject.toml ]] || [[ -f setup.py ]]; then
        python3 -m pip install --upgrade build >/dev/null 2>&1 || true
        python3 -m build -w -o "$OUT_DIR/python" 2>/dev/null || true
      fi
    fi
    ;;

  rust)
    echo "Compilando Rust (release)..."
    if command -v cargo >/dev/null 2>&1; then
      cargo build --release
      if [[ -d target/release ]]; then cp -r target/release "$OUT_DIR/"; fi
    else
      echo "cargo no está disponible en PATH"; exit 1
    fi
    ;;

  make)
    echo "Makefile detectado. Ejecutando 'make build' si existe..."
    if make -n build >/dev/null 2>&1; then
      make build
      # El usuario debe colocar artefactos en build/ o bin/
      if [[ -d build ]]; then cp -r build "$OUT_DIR/"; fi
      if [[ -d bin ]]; then cp -r bin "$OUT_DIR/"; fi
    else
      echo "No hay objetivo build en Makefile o make no está disponible"
    fi
    ;;

  *)
    echo "Tipo de proyecto no soportado por autodetección. Empaquetando repo entero salvo .git..."
    ;;
esac

echo "Empaquetando artefactos en $OUT_TAR..."
# Incluir archivos generados; si no hay, empaquetar todo salvo .git
if [[ -n "$(ls -A "$OUT_DIR" 2>/dev/null || true)" ]]; then
  tar -C "$OUT_DIR" -czf "$OUT_TAR" .
else
  tar --exclude='.git' -czf "$OUT_TAR" .
fi

echo "Archivo creado: $OUT_TAR"

deploy_via_cli() {
  if command -v faro >/dev/null 2>&1; then
    echo "Usando Faro CLI para desplegar..."
    if [[ -n "${FARO_HOST:-}" ]]; then
      export FARO_HOST
    fi
    if [[ -n "${FARO_TOKEN:-}" ]]; then
      export FARO_TOKEN
    fi
    faro deploy --app "$APP_NAME" --env "$ENVIRONMENT" --file "$OUT_TAR"
    return $?
  fi
  return 2
}

deploy_via_api() {
  if [[ -n "${FARO_HOST:-}" ]] && [[ -n "${FARO_TOKEN:-}" ]]; then
    echo "Subiendo $OUT_TAR a $FARO_HOST via API..."
    curl -sS -X POST "$FARO_HOST/api/v1/deploy" \
      -H "Authorization: Bearer $FARO_TOKEN" \
      -F "app=$APP_NAME" \
      -F "env=$ENVIRONMENT" \
      -F "file=@$OUT_TAR"
    return $?
  fi
  return 2
}

echo "Intentando desplegar..."
if deploy_via_cli; then
  echo "Despliegue iniciado (CLI)."
  exit 0
fi

if deploy_via_api; then
  echo "Despliegue iniciado (API)."
  exit 0
fi

echo "No se pudo desplegar: ni Faro CLI disponible ni FARO_HOST/FARO_TOKEN proporcionados."
echo "Opciones: instalar Faro CLI y autenticarse, o exportar FARO_HOST y FARO_TOKEN antes de ejecutar el script."
exit 1
