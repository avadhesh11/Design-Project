import axios from "axios";

const rawApiUrl = process.env.NEXT_PUBLIC_API_URL;
const baseApiUrl = rawApiUrl
  ? (rawApiUrl.endsWith("/api") ? rawApiUrl : `${rawApiUrl}/api`)
  : "http://localhost:8000/api";

const api = axios.create({
  baseURL: baseApiUrl,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true,
});
api.interceptors.response.use(
  (res) => res,

  async (err) => {
    const originalRequest = err.config;

    // Exclude auth endpoints from auto-refresh to preserve actual login/registration errors
    const isAuthEndpoint =
      originalRequest?.url?.includes("/auth/login") ||
      originalRequest?.url?.includes("/auth/register") ||
      originalRequest?.url?.includes("/auth/refresh");

    // Prevent retry loop
    if (
      err.response?.status === 401 &&
      !originalRequest._retry &&
      !isAuthEndpoint
    ) {
      originalRequest._retry = true;

      try {
        await api.post("/auth/refresh");

        return api(originalRequest);

      } catch (refreshError) {
        const publicPaths = ["/", "/login", "/register"];
        if (
          typeof window !== "undefined" &&
          !publicPaths.includes(window.location.pathname)
        ) {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(err);
  }
);

export default api;