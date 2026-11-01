"""
Dristik AI Progressive Phase-wise Report Endpoints.
Serves live sub-phase and consolidated phase report catalogs, JSON contracts,
and immutable rendered PDF downloads.
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.identity.access import require_analysis
from app.identity.authorizer import UserIdentity
from app.identity.deps import get_current_user
from app.reporting.engines.pdf_renderer import ProgressivePDFRenderer
from app.reporting.engines.report_registry import get_report_registry
from app.reporting.storage.report_storage import get_report_storage

logger = logging.getLogger("dristik.api.reports_progressive")

router = APIRouter(prefix="/analyses", tags=["Progressive Reports"])


@router.get("/{analysis_id}/reports/catalog")
async def get_progressive_reports_catalog(
    analysis_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Returns catalog of all available and in-progress sub-phase and phase reports."""
    require_analysis(analysis_id, user)
    registry = get_report_registry()
    return registry.get_catalog(analysis_id)


@router.get("/{analysis_id}/phases/{phase_id}/subphases/{subphase_id}/json")
async def get_subphase_contract_json(
    analysis_id: str,
    phase_id: str,
    subphase_id: str,
    user: UserIdentity = Depends(get_current_user),
):
    """Returns raw source-of-truth JSON contract for a specific sub-phase."""
    require_analysis(analysis_id, user)
    storage = get_report_storage()
    contract = storage.load_subphase_json(analysis_id, phase_id, subphase_id)
    if not contract:
        raise HTTPException(
            status_code=404,
            detail=f"Sub-phase report {subphase_id} for phase {phase_id} has not yet executed or is not found.",
        )
    return contract.model_dump(mode="json")


@router.get("/{analysis_id}/phases/{phase_id}/subphases/{subphase_id}/pdf")
async def download_subphase_pdf(
    analysis_id: str,
    phase_id: str,
    subphase_id: str,
    disposition: str = Query(default="inline", pattern="^(inline|attachment)$"),
    user: UserIdentity = Depends(get_current_user),
):
    """Downloads or previews the immutable rendered PDF for a sub-phase."""
    require_analysis(analysis_id, user)
    storage = get_report_storage()
    clean_sub_id = subphase_id.replace(".", "_")

    pdf_path = storage.get_subphase_pdf_path(analysis_id, phase_id, subphase_id)
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    else:
        # Render on demand from persisted JSON contract if PDF was not generated yet
        contract = storage.load_subphase_json(analysis_id, phase_id, subphase_id)
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Sub-phase report {subphase_id} not available for download.",
            )
        html_content = ProgressivePDFRenderer.render_subphase_html(contract)
        pdf_bytes = await ProgressivePDFRenderer.render_pdf(html_content)
        if not pdf_bytes:
            # Fallback: Return HTML preview if PDF rendering is unavailable
            return Response(content=html_content, media_type="text/html")
        storage.save_subphase_pdf(analysis_id, phase_id, subphase_id, pdf_bytes, clean_sub_id)

    filename = f"dristik_{analysis_id}_subphase_{clean_sub_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )


@router.get("/{analysis_id}/phases/{phase_id}/pdf")
async def download_consolidated_phase_pdf(
    analysis_id: str,
    phase_id: str,
    disposition: str = Query(default="inline", pattern="^(inline|attachment)$"),
    user: UserIdentity = Depends(get_current_user),
):
    """Downloads or previews the consolidated Phase PDF."""
    require_analysis(analysis_id, user)
    storage = get_report_storage()

    pdf_path = storage.get_phase_pdf_path(analysis_id, phase_id)
    if pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
    else:
        contract = storage.load_phase_json(analysis_id, phase_id)
        if not contract:
            raise HTTPException(
                status_code=404,
                detail=f"Consolidated phase report for {phase_id} is not yet available.",
            )
        html_content = ProgressivePDFRenderer.render_phase_html(contract)
        pdf_bytes = await ProgressivePDFRenderer.render_pdf(html_content)
        if not pdf_bytes:
            return Response(content=html_content, media_type="text/html")
        storage.save_phase_pdf(analysis_id, phase_id, pdf_bytes, "complete")

    filename = f"dristik_{analysis_id}_{phase_id}_consolidated.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{disposition}; filename="{filename}"'},
    )
