import os
import shutil
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, text

from autocub.core.logging import logger
from autocub.core.config import settings
from autocub.database.connection import SessionLocal
from autocub.database.models import CubMensal, Sinduscon, EtlExecucao

try:
    import psutil
except ImportError:
    psutil = None


def get_dir_size_and_count(directory_path: str):
    """Calcula tamanho total em bytes e quantidade de arquivos em um diretório."""
    total_size = 0
    total_count = 0
    if not os.path.exists(directory_path):
        return 0, 0
    for root, _, files in os.walk(directory_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_size += os.path.getsize(fp)
                if f.lower().endswith(".pdf"):
                    total_count += 1
            except (OSError, IOError):
                pass
    return total_size, total_count


def generate_etl_audit_summary(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Gera auditoria forense e telemetria de infraestrutura completa do ETL.
    Consolida eficiência, falhas, conciliação de banco, espaço físico e consumo de hardware.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        # 1. Eficiência de Execuções ETL
        total_execs = db.query(func.count(EtlExecucao.id)).scalar() or 0
        sucesso_count = (
            db.query(func.count(EtlExecucao.id))
            .filter(EtlExecucao.status == "SUCESSO")
            .scalar()
            or 0
        )
        cache_count = (
            db.query(func.count(EtlExecucao.id))
            .filter(EtlExecucao.status == "CACHE_LOCAL")
            .scalar()
            or 0
        )
        falha_count = (
            db.query(func.count(EtlExecucao.id))
            .filter(EtlExecucao.status == "FALHA")
            .scalar()
            or 0
        )
        nao_suportado_count = (
            db.query(func.count(EtlExecucao.id))
            .filter(EtlExecucao.status == "NAO_SUPORTADO_CBIC")
            .scalar()
            or 0
        )

        taxa_sucesso = (
            round(((sucesso_count + cache_count) / total_execs) * 100, 1)
            if total_execs > 0
            else 0.0
        )

        # Categorização dos principais motivos de falha
        falhas_query = (
            db.query(
                EtlExecucao.mensagem_erro,
                func.count(EtlExecucao.id).label("qtd")
            )
            .filter(EtlExecucao.status == "FALHA")
            .group_by(EtlExecucao.mensagem_erro)
            .order_by(desc("qtd"))
            .limit(5)
            .all()
        )
        top_falhas = [
            {"motivo": f[0] or "Erro não discriminado", "ocorrencias": f[1]}
            for f in falhas_query
        ]

        # 2. Volume & Conciliação de Dados (PostgreSQL)
        total_cotacoes = db.query(func.count()).select_from(CubMensal).scalar() or 0

        # Cotações agrupadas por ano
        anos_stats = (
            db.query(
                func.extract("year", CubMensal.data_referencia).label("ano"),
                func.count(func.distinct(CubMensal.data_referencia)).label("meses"),
                func.count(func.distinct(CubMensal.sinduscon_id)).label("sinduscons"),
                func.count().label("total")
            )
            .group_by("ano")
            .order_by(desc("ano"))
            .all()
        )
        cotacoes_por_ano = [
            {
                "ano": int(a[0]),
                "meses_distintos": a[1],
                "sinduscons": a[2],
                "total_cotacoes": a[3]
            }
            for a in anos_stats
        ]

        # Sindicatos ativos vs com dados
        sinduscons_ativos = db.query(Sinduscon).filter(Sinduscon.ativo == True).count()
        sinduscons_com_dados = (
            db.query(func.count(func.distinct(CubMensal.sinduscon_id))).scalar() or 0
        )

        # 3. Ocupação de Espaço Físico & Disco
        downloads_dir = settings.CUB_DOWNLOAD_DIR
        bytes_downloads, total_pdfs = get_dir_size_and_count(downloads_dir)
        mb_downloads = round(bytes_downloads / (1024 * 1024), 2)

        # Tamanho do banco PostgreSQL
        pg_db_size = "N/A"
        try:
            res = db.execute(text("SELECT pg_size_pretty(pg_database_size(current_database()));")).scalar()
            if res:
                pg_db_size = str(res)
        except Exception:
            pass

        # Espaço em disco da partição
        disco_total_gb = 0.0
        disco_livre_gb = 0.0
        disco_usado_pct = 0.0
        try:
            usage = shutil.disk_usage(os.path.abspath(downloads_dir) if os.path.exists(downloads_dir) else ".")
            disco_total_gb = round(usage.total / (1024**3), 2)
            disco_livre_gb = round(usage.free / (1024**3), 2)
            disco_usado_pct = round(((usage.total - usage.free) / usage.total) * 100, 1)
        except Exception:
            pass

        # 4. Consumo de Processamento, Memória & Rede
        hardware_telemetry = {
            "cpu_percent": None,
            "memory_process_mb": None,
            "memory_system_percent": None,
            "network_bytes_sent_mb": None,
            "network_bytes_recv_mb": None
        }

        if psutil:
            try:
                proc = psutil.Process()
                hardware_telemetry["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                mem_info = proc.memory_info()
                hardware_telemetry["memory_process_mb"] = round(mem_info.rss / (1024 * 1024), 2)
                hardware_telemetry["memory_system_percent"] = psutil.virtual_memory().percent
                net_io = psutil.net_io_counters()
                if net_io:
                    hardware_telemetry["network_bytes_sent_mb"] = round(net_io.bytes_sent / (1024 * 1024), 2)
                    hardware_telemetry["network_bytes_recv_mb"] = round(net_io.bytes_recv / (1024 * 1024), 2)
            except Exception as pe:
                logger.debug(f"Aviso capturando telemetria psutil: {pe}")

        report_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eficiencia": {
                "total_execucoes": total_execs,
                "sucesso_downloads": sucesso_count,
                "reaproveitamento_cache": cache_count,
                "falhas": falha_count,
                "nao_suportado_cbic": nao_suportado_count,
                "taxa_eficiencia_pct": taxa_sucesso,
                "top_motivos_falha": top_falhas
            },
            "conciliacao_banco": {
                "total_cotacoes_postgres": total_cotacoes,
                "sinduscons_ativos": sinduscons_ativos,
                "sinduscons_com_dados": sinduscons_com_dados,
                "distribuicao_por_ano": cotacoes_por_ano
            },
            "armazenamento_fisico": {
                "total_pdfs_em_disco": total_pdfs,
                "tamanho_pasta_downloads_mb": mb_downloads,
                "tamanho_banco_postgres": pg_db_size,
                "disco_total_gb": disco_total_gb,
                "disco_livre_gb": disco_livre_gb,
                "disco_usado_pct": disco_usado_pct
            },
            "hardware_telemetria": hardware_telemetry
        }

        # 5. Formatação do Relatório Visual em Markdown
        md_lines = [
            "================================================================================",
            "📋 RELATÓRIO CONSOLIDADO DE AUDITORIA FORENSE & TELEMETRIA DO ETL",
            f"🕒 Timestamp: {report_data['timestamp']} UTC",
            "================================================================================",
            f"⚡ EFICIÊNCIA & EXECUÇÕES:",
            f"   • Total de relatórios processados : {total_execs}",
            f"   • Sucessos (Downloads novos)     : {sucesso_count}",
            f"   • Reaproveitamentos (Cache local) : {cache_count}",
            f"   • Falhas operacionais ou ausentes : {falha_count}",
            f"   • Taxa de Eficiência Global       : {taxa_sucesso}%",
            "",
            f"💾 VOLUME & CONCILIAÇÃO POSTGRESQL:",
            f"   • Total de cotações ativas no banco: {total_cotacoes}",
            f"   • Sindicatos ativos cadastrados    : {sinduscons_ativos} (com dados: {sinduscons_com_dados})",
        ]

        for ano_info in cotacoes_por_ano[:4]:
            md_lines.append(
                f"   • Ano {ano_info['ano']}: {ano_info['total_cotacoes']} cotações "
                f"({ano_info['meses_distintos']} meses, {ano_info['sinduscons']} sindicatos)"
            )

        md_lines.extend([
            "",
            f"📁 ARMAZENAMENTO & OCUPAÇÃO DE ESPAÇO:",
            f"   • Relatórios oficiais em PDF : {total_pdfs} arquivos ({mb_downloads} MB)",
            f"   • Tamanho do Banco PostgreSQL: {pg_db_size}",
            f"   • Partição de Armazenamento  : {disco_livre_gb} GB livres de {disco_total_gb} GB ({disco_usado_pct}% ocupado)",
            "",
            f"🖥️ HARDWARE & RECURSOS:",
            f"   • Memória RAM do processo : {hardware_telemetry['memory_process_mb']} MB (Uso Geral: {hardware_telemetry['memory_system_percent']}%)",
            f"   • Carga de CPU do Sistema : {hardware_telemetry['cpu_percent']}%",
            f"   • Tráfego de Rede Global  : {hardware_telemetry['network_bytes_recv_mb']} MB (RX) / {hardware_telemetry['network_bytes_sent_mb']} MB (TX)",
        ])

        if top_falhas:
            md_lines.extend([
                "",
                "🔍 PRINCIPAIS MOTIVOS DE FALHA / ALERTAS CAPTURADOS:",
            ])
            for idx, item in enumerate(top_falhas, start=1):
                md_lines.append(f"   {idx}. [{item['ocorrencias']}x] {item['motivo']}")

        md_lines.append("================================================================================")
        formatted_summary = "\n".join(md_lines)

        # Emite no Logger
        logger.info("\n" + formatted_summary)

        # Salva em disco para persistência
        try:
            os.makedirs(downloads_dir, exist_ok=True)
            report_json_path = os.path.join(downloads_dir, "etl_audit_latest.json")
            report_md_path = os.path.join(downloads_dir, "etl_audit_latest.md")
            with open(report_json_path, "w", encoding="utf-8") as fj:
                json.dump(report_data, fj, indent=2, ensure_ascii=False)
            with open(report_md_path, "w", encoding="utf-8") as fm:
                fm.write(formatted_summary)
        except Exception as fe:
            logger.warning(f"Não foi possível salvar arquivos de auditoria em disco: {fe}")

        return report_data

    finally:
        if close_db:
            db.close()
