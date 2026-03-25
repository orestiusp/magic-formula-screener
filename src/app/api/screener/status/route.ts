import { NextRequest, NextResponse } from "next/server";
import { getJob } from "@/lib/job-store";
import { JobStatusResponse } from "@/lib/types";

export async function GET(request: NextRequest) {
  const jobId = request.nextUrl.searchParams.get("jobId");

  if (!jobId) {
    return NextResponse.json({ error: "Missing jobId parameter" }, { status: 400 });
  }

  const job = getJob(jobId);
  if (!job) {
    return NextResponse.json({ error: "Job not found" }, { status: 404 });
  }

  const response: JobStatusResponse = {
    jobId: job.jobId,
    status: job.status,
    progress: job.progress,
    error: job.error,
  };

  return NextResponse.json(response);
}
