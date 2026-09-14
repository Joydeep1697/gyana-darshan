import { apiFetch } from "../utils/api";

export async function setupPushNotifications() {
  if (!("serviceWorker" in navigator) || !("Notification" in window)) return;
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return;
  const registration = await navigator.serviceWorker.ready;
  const subscription = await registration.pushManager.getSubscription();
  await apiFetch("/api/notifications/push-subscribe", { method: "POST", body: JSON.stringify({ subscription: subscription ? subscription.toJSON() : { mode: "stub" } }) });
}

export async function showLocalNotification(title: string, body: string, data: { matter_id?: string }) {
  if (!("serviceWorker" in navigator)) return;
  const registration = await navigator.serviceWorker.ready;
  await registration.showNotification(title, { body, data });
}
