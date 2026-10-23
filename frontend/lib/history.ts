import { getJson } from "@/lib/corpus";
import type { ConversationDetail, ConversationSummary } from "@/lib/present";

const NOT_FOUND = "That conversation doesn't exist.";

export async function listConversations(): Promise<ConversationSummary[]> {
  const body = (await getJson("/api/conversations", NOT_FOUND)) as { conversations: ConversationSummary[] };
  return body.conversations;
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  return (await getJson(`/api/conversations/${encodeURIComponent(conversationId)}`, NOT_FOUND)) as ConversationDetail;
}
