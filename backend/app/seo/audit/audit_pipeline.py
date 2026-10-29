from app.seo.audit.orchestrator import SEOAuditOrchestrator

async def execute_audit_pipeline(audit_id: str, domain: str):
    orchestrator = SEOAuditOrchestrator(audit_id=audit_id, domain=domain)
    return await orchestrator.run()
