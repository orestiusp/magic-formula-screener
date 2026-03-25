import { JobState } from "./types";

const jobs = new Map<string, JobState>();

const JOB_TTL_MS = 60 * 60 * 1000; // 1 hour

export function createJob(jobId: string, outputPath: string): JobState {
  const job: JobState = {
    jobId,
    status: "pending",
    progress: "",
    outputPath,
    createdAt: Date.now(),
  };
  jobs.set(jobId, job);
  // Auto-cleanup after TTL
  setTimeout(() => {
    jobs.delete(jobId);
  }, JOB_TTL_MS);
  return job;
}

export function getJob(jobId: string): JobState | undefined {
  return jobs.get(jobId);
}

export function updateJob(jobId: string, updates: Partial<JobState>): void {
  const job = jobs.get(jobId);
  if (job) {
    Object.assign(job, updates);
  }
}

export function hasRunningJob(): boolean {
  for (const job of jobs.values()) {
    if (job.status === "running" || job.status === "pending") {
      return true;
    }
  }
  return false;
}
