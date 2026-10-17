from app.seo.audit.orchestration.dag import AuditDAG

def test_audit_dag_structure():
    dag = AuditDAG()
    assert len(dag.nodes) >= 30
    ready = dag.get_ready_nodes(set())
    assert any(n.agent_id == '01' for n in ready)
