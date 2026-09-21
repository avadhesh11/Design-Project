"use client";

import React from "react";

export function LoadingScreen({
  title = "Loading...",
  subtitle = "Preparing your workspace",
}: {
  title?: string;
  subtitle?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] w-full p-8 animate-fade-up">
      <div className="flex items-center gap-3 mb-3">
        <Spinner className="w-5 h-5 text-orbit-muted" />
        <h3 className="text-sm font-medium text-orbit-text">{title}</h3>
      </div>
      <p className="text-xs text-orbit-muted">{subtitle}</p>
    </div>
  );
}

function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div className={`bg-surface2 border border-orbit-border rounded-md animate-pulse ${className}`} />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8 animate-fade-up">
      {/* Header */}
      <div className="space-y-2">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-7 w-56" />
        <Skeleton className="h-4 w-36" />
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
      </div>

      {/* Two col */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-3">
          <Skeleton className="h-4 w-36" />
          <Skeleton className="h-48 rounded-lg" />
        </div>
        <div className="space-y-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-48 rounded-lg" />
        </div>
      </div>

      {/* AI strip */}
      <Skeleton className="h-16 rounded-lg" />
    </div>
  );
}

export function DocumentsSkeleton() {
  return (
    <div className="max-w-3xl mx-auto p-6 space-y-5 animate-fade-up">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-6 w-40" />
        </div>
        <Skeleton className="h-8 w-32 rounded-md" />
      </div>
      <div className="orbit-card overflow-hidden divide-y divide-orbit-border">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-3 px-4 py-3">
            <Skeleton className="h-3.5 w-3.5 rounded flex-shrink-0" />
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-3.5 w-48" />
              <Skeleton className="h-2.5 w-24" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function TasksSkeleton() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-5 animate-fade-up">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-3 w-14" />
          <Skeleton className="h-6 w-28" />
        </div>
        <Skeleton className="h-8 w-24 rounded-md" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((col) => (
          <div key={col} className="rounded-lg border border-orbit-border bg-surface2/30 overflow-hidden">
            <div className="flex items-center gap-2 px-3.5 py-2.5 border-b border-orbit-border bg-surface">
              <Skeleton className="h-1.5 w-1.5 rounded-full" />
              <Skeleton className="h-3.5 w-20" />
            </div>
            <div className="p-2.5 space-y-2">
              <Skeleton className="h-20 rounded-lg" />
              <Skeleton className="h-20 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function IntegrationsSkeleton() {
  return (
    <div className="p-6 max-w-5xl space-y-5 animate-fade-up">
      <div className="space-y-2">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-6 w-44" />
      </div>
      <Skeleton className="h-24 rounded-lg" />
      <Skeleton className="h-36 rounded-lg" />
      <Skeleton className="h-60 rounded-lg" />
    </div>
  );
}
