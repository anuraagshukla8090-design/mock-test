import api from './client'
import type { IngestionDetail, IngestionListItem } from '../types/ingestion'

export const getLayouts = () =>
  api.get<Record<string, string>>('/ingestion/layouts').then((r) => r.data)

export const getIngestions = (skip = 0, limit = 100) =>
  api.get<IngestionListItem[]>('/ingestion/history', { params: { skip, limit } }).then((r) => r.data)

export const getIngestionStatus = (id: string) =>
  api.get<IngestionDetail>(`/ingestion/${id}/status`).then((r) => r.data)

export const uploadPdf = (formData: FormData) =>
  api.post<IngestionDetail>('/ingestion/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((r) => r.data)

export const retryIngestion = (id: string) =>
  api.post<IngestionDetail>(`/ingestion/${id}/retry`).then((r) => r.data)
