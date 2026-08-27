import {apiClient, type ApiRequestOptions} from "@/lib/api/client";

export type NotificationRecord = {
  created_at: string;
  data: Record<string, unknown> | null;
  id: string;
  is_read: boolean;
  message: string;
  notification_type: string;
  read_at: string | null;
  title: string;
};

export const notificationsApi = {
  listMine: (options: ApiRequestOptions) => apiClient.get<NotificationRecord[]>("/notifications", options),
  markRead: (id: string, options: ApiRequestOptions) => apiClient.patch<NotificationRecord>("/notifications/" + id + "/read", undefined, options)
};
