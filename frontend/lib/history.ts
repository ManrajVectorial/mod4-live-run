import { getJson } from "@/lib/corpus";
import { historyNotFound, type ConversationDetail, type ConversationSummary } from "@/lib/present";

export async function listConversations(): Promise<ConversationSummary[]> {
  const body = (await getJson("/api/conversations", historyNotFound)) as { conversations: ConversationSummary[] };
  return body.conversations;
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return (await getJson(`/api/conversations/${encodeURIComponent(conversationId)}`, historyNotFound)) as ConversationDetail;
}
