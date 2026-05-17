import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export const uploadVideo = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const res = await api.post('/jobs/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return res.data;
};

export const analyzeVideo = async (jobId: string) => {
  const res = await api.post(`/jobs/${jobId}/analyze`);
  return res.data;
};

export const getAnalysis = async (jobId: string) => {
  const res = await api.get(`/jobs/${jobId}/analysis`);
  return res.data;
};

export const editVideo = async (jobId: string, prompt: string) => {
  const res = await api.post(`/jobs/${jobId}/edit`, { prompt });
  return res.data;
};

export const renderVideo = async (jobId: string) => {
  const res = await api.post(`/jobs/${jobId}/render`);
  return res.data;
};

export const getStatus = async (jobId: string) => {
  const res = await api.get(`/jobs/${jobId}/status`);
  return res.data;
};
