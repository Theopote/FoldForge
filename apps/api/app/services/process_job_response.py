"""Build API responses for papercraft process job polling."""

from app.schemas.process_job import ProcessJob, ProcessJobResponse


def build_process_job_response(job: ProcessJob) -> ProcessJobResponse:
    return ProcessJobResponse(
        jobId=job.id,
        projectId=job.project_id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
        async_mode=True,
        processedModelUrl=job.processed_model_url,
        unfoldSvgUrl=job.unfold_svg_url,
        unfoldPdfUrl=job.unfold_pdf_url,
        unfoldZipUrl=job.unfold_zip_url,
        resultStatus=job.result_status,
        stats=job.stats,
        craftability=job.craftability,
    )
