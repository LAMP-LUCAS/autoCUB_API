#!/bin/bash
set -e
set -u

function create_user_and_database() {
    local database=$1
    echo "  Configurando banco e usuário '$database'..."
    local password=""
    if [ "$database" = "kong" ]; then
        password="${KONG_PG_PASSWORD:-kong_pass}"
    else
        password="${POSTGRES_PASSWORD:-autocub_pass}"
    fi

    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$database') THEN
                CREATE ROLE $database WITH LOGIN PASSWORD '$password';
            ELSE
                ALTER ROLE $database WITH LOGIN PASSWORD '$password';
            END IF;
        END
        \$\$;

        SELECT 'CREATE DATABASE $database OWNER $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec

        GRANT ALL PRIVILEGES ON DATABASE $database TO $database;
EOSQL
}

if [ -n "${POSTGRES_MULTIPLE_DATABASES:-}" ]; then
    echo "Criação de múltiplos bancos solicitada: $POSTGRES_MULTIPLE_DATABASES"
    for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
        create_user_and_database "$db"
    done
    echo "Múltiplos bancos de dados inicializados com sucesso."
fi
