import React, { useState, useEffect } from "react";
import { Activity, Server, Monitor, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import ChatPanel from "@/components/ChatPanel";
import ExplorerPanel from "@/components/ExplorerPanel";
import { healthCheck } from "@/lib/api";

export default function App() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    healthCheck()
      .then(setHealth)
      .catch(() => setHealth({ status: "disconnected" }));
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Zap className="h-5 w-5 text-primary" />
            <h1 className="text-lg font-semibold">MCP Client Demo</h1>
          </div>
          <Badge variant="outline" className="text-xs">v1.0</Badge>
        </div>

        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {health && (
            <>
              <div className="flex items-center gap-1">
                <Activity className={`h-3 w-3 ${health.mcp_connected ? "text-green-500" : "text-red-500"}`} />
                MCP {health.mcp_connected ? "Connected" : "Disconnected"}
              </div>
              <div className="flex items-center gap-1">
                <Server className="h-3 w-3" />
                {health.tools_count} tools, {health.resources_count} resources, {health.prompts_count} prompts
              </div>
            </>
          )}
        </div>
      </header>

      {/* Main content — two-column layout */}
      <main className="flex-1 flex min-h-0">
        {/* Left: Chat */}
        <div className="flex-1 p-4 flex flex-col min-h-0">
          <ChatPanel />
        </div>

        {/* Right: Explorer */}
        <div className="w-[420px] border-l p-4 flex flex-col min-h-0">
          <ExplorerPanel />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t px-6 py-2 text-center text-xs text-muted-foreground">
        <div className="flex items-center justify-center gap-4">
          <span className="flex items-center gap-1">
            <Monitor className="h-3 w-3" /> React + shadcn/ui
          </span>
          <span>|</span>
          <span className="flex items-center gap-1">
            <Server className="h-3 w-3" /> FastAPI + MCP
          </span>
          <span>|</span>
          <span>Powered by Claude</span>
        </div>
      </footer>
    </div>
  );
}
