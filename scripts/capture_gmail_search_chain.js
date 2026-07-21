"use strict";

// Convert Gmail search_email_ids calls already recorded in one Codex rollout
// into private connector pages. The script prints counts only: never message
// ids, account values, queries, or cursor tokens.

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const readline = require("readline");

const [
  sessionPath,
  outputDir,
  prefix,
  query,
  accountTemplatePath,
  authorizedFrom = "",
] =
  process.argv.slice(2);
if (!sessionPath || !outputDir || !prefix || !query || !accountTemplatePath) {
  process.exit(2);
}
if (
  authorizedFrom &&
  !/^\d{4}-\d{2}-\d{2}$/.test(authorizedFrom)
) {
  process.exit(3);
}

function digest(value) {
  return `sha256:${crypto
    .createHash("sha256")
    .update(JSON.stringify(value))
    .digest("hex")}`;
}

function parseArguments(value) {
  if (value && typeof value === "object") return value;
  try {
    return JSON.parse(String(value || "{}"));
  } catch {
    return {};
  }
}

async function main() {
const calls = new Map();
const orderedCallIds = [];
const results = new Map();
const lines = readline.createInterface({
  input: fs.createReadStream(sessionPath, { encoding: "utf8" }),
  crlfDelay: Infinity,
});
for await (const line of lines) {
  if (!line) continue;
  let entry;
  try {
    entry = JSON.parse(line);
  } catch {
    continue;
  }
  const payload = entry.payload || {};
  if (
    payload.type === "function_call" &&
    payload.name === "_search_email_ids"
  ) {
    const args = parseArguments(payload.arguments);
    if (String(args.query || "") !== query) continue;
    calls.set(payload.call_id, args);
    orderedCallIds.push(payload.call_id);
    continue;
  }
  if (payload.type !== "mcp_tool_call_end") continue;
  const content = payload?.result?.Ok?.structuredContent;
  if (calls.has(payload.call_id) && Array.isArray(content?.message_ids)) {
    results.set(payload.call_id, content);
  }
}

const chain = orderedCallIds.map((callId) => ({
  args: calls.get(callId),
  result: results.get(callId),
}));
if (!chain.length || chain.some((item) => !item.result)) {
  process.exit(4);
}

const seenCursors = new Set();
const seenIds = new Set();
let previousNext = "";
let rowCount = 0;
for (let index = 0; index < chain.length; index += 1) {
  const { args, result } = chain[index];
  const requested = String(args.next_page_token || "");
  if (requested !== previousNext) process.exit(5);
  if (requested && seenCursors.has(requested)) process.exit(6);
  if (requested) seenCursors.add(requested);
  const next = String(result.next_page_token || "");
  if (index < chain.length - 1 && !next) process.exit(7);
  if (index === chain.length - 1 && next) process.exit(8);
  for (const id of result.message_ids) {
    if (!id || seenIds.has(id)) process.exit(9);
    seenIds.add(id);
    rowCount += 1;
  }
  previousNext = next;
}

const template = JSON.parse(
  fs.readFileSync(accountTemplatePath, "utf8"),
);
fs.mkdirSync(outputDir, { recursive: true });
const written = [];
for (let index = 0; index < chain.length; index += 1) {
  const { args, result } = chain[index];
  const requested = String(args.next_page_token || "");
  const next = String(result.next_page_token || "");
  const terminal = !next;
  const page = {
    query,
    account: template.account,
    authorization_revision:
      template.authorization_revision || "connector-read:v1",
    policy_revision: template.policy_revision || "policy:v1",
    authorized_from: authorizedFrom,
    coverage: terminal ? "complete" : "partial",
    terminal,
    requested_page_token: requested,
    next_page_token: next || null,
    messages: result.message_ids.map((id) => ({
      id,
      thread_id: null,
      from_: null,
      to: [],
      subject: null,
      snippet: null,
      body: null,
      labels: null,
      email_ts: null,
      attachments: [],
      content_status: "identity_only",
      identity_only: true,
    })),
    denied_object_ids: [],
    connector_status: "identity_only_complete",
    gap_reason: "gmail_message_metadata_not_requested",
  };
  const filename = `${prefix}-page-${String(index + 1).padStart(3, "0")}.json`;
  const outputPath = path.join(outputDir, filename);
  const tempPath = `${outputPath}.tmp`;
  fs.writeFileSync(tempPath, `${JSON.stringify(page, null, 2)}\n`, "utf8");
  fs.renameSync(tempPath, outputPath);
  written.push(filename);
}

const receipt = {
  artifact_type: "matters.gmail-search-chain-receipt.v1",
  status: "complete",
  safe_terminal_coverage: true,
  query_fingerprint: digest(query),
  account_ref: digest(template.account),
  authorized_from: authorizedFrom,
  page_count: chain.length,
  unique_message_count: seenIds.size,
  cursor_chain_verified: true,
  terminal: true,
  message_set_fingerprint: digest([...seenIds].sort()),
  page_inventory_fingerprint: digest(written),
  content_claim: "identity_only",
  claim_boundary:
    "Complete covers only the exact Gmail query fingerprint and message-id enumeration. Message metadata and content were not requested.",
};
const receiptPath = path.join(outputDir, `${prefix}-coverage-receipt.json`);
const receiptTempPath = `${receiptPath}.tmp`;
fs.writeFileSync(
  receiptTempPath,
  `${JSON.stringify(receipt, null, 2)}\n`,
  "utf8",
);
fs.renameSync(receiptTempPath, receiptPath);
process.stdout.write(
  JSON.stringify({
    status: receipt.status,
    page_count: receipt.page_count,
    unique_message_count: receipt.unique_message_count,
    cursor_chain_verified: receipt.cursor_chain_verified,
    terminal: receipt.terminal,
  }),
);
}

main().catch(() => {
  process.exitCode = 10;
});
