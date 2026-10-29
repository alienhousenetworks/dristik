import asyncio
from typing import Dict, Any

class TaskExecutor:
    async def execute_task(self, agent_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.01)
        return {"agent_id": agent_id, "status": "SUCCESS"}
