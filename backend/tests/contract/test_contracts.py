from app.seo.audit.contracts import AgentOutput, FindingContract
from app.core.enums import FindingCategory, FindingSeverity

def test_finding_contract_validation():
    f = FindingContract(
        id='fnd_test',
        category=FindingCategory.TECHNICAL,
        severity=FindingSeverity.HIGH,
        title='Test Canonical Gap'
    )
    output = AgentOutput(
        agent_id='04',
        agent_name='Crawlability and Indexation',
        findings=[f]
    )
    assert output.status == 'COMPLETED'
    assert len(output.findings) == 1
