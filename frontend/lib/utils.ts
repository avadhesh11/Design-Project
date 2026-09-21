import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function parseUtcDate(date: string | Date | null | undefined): Date {
  if (!date) return new Date();
  if (date instanceof Date) return date;

  const dateStr = String(date).trim();
  // If ISO string like "2026-09-14T05:04:22" without Z or timezone offset
  if (dateStr.includes("T") && !dateStr.endsWith("Z") && !/[+-]\d{2}:\d{2}$/.test(dateStr)) {
    return new Date(`${dateStr}Z`);
  }

  // If SQL timestamp like "2026-09-14 05:04:22"
  if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}/.test(dateStr) && !dateStr.endsWith("Z") && !/[+-]\d{2}/.test(dateStr)) {
    return new Date(`${dateStr.replace(" ", "T")}Z`);
  }

  return new Date(dateStr);
}

export function formatDate(date: string | Date) {
  const d = parseUtcDate(date);
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric" }).format(d);
}

export function formatTime(iso: string) {
  const date = parseUtcDate(iso);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();
  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  const isYesterday = date.toDateString() === yesterday.toDateString();

  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  if (isToday) return `Today ${time}`;
  if (isYesterday) return `Yesterday ${time}`;
  return date.toLocaleDateString([], { month: "short", day: "numeric" }) + " " + time;
}

export function formatRelative(date: string | Date) {
  const now = new Date();
  const d = parseUtcDate(date);
  const diff = now.getTime() - d.getTime();
  const mins = Math.floor(diff / 60000);

  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function getInitial(email: string) {
  return email?.[0]?.toUpperCase() || "?";
}

export function getAvatarColor(email: string) {
  const colors = ["#7fffb2", "#5b8aff", "#ffd166", "#ff6b6b", "#c084fc"];
  return colors[(email?.charCodeAt(0) || 0) % colors.length];
}
