import type { Health } from "../types/api";
import { get } from "./client";

export const fetchHealth = (signal?: AbortSignal) => get<Health>("/health", signal);