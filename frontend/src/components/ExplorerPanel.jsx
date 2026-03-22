import React, { useState, useEffect } from "react";
import {
  Wrench,
  FileText,
  MessageSquare,
  RefreshCw,
  Play,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  listTools,
  listResources,
  listPrompts,
  callTool,
  readResource,
  getPrompt,
} from "@/lib/api";

export default function ExplorerPanel() {
  const [tab, setTab] = useState("tools");
  const [tools, setTools] = useState([]);
  const [resources, setResources] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const [t, r, p] = await Promise.all([listTools(), listResources(), listPrompts()]);
      setTools(t.tools || []);
      setResources(r.resources || []);
      setPrompts(p.prompts || []);
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  // ---- Quick-call handlers ----

  const handleCallTool = async (toolName) => {
    setResult(null);
    setLoading(true);
    try {
      // Provide sensible demo arguments
      const demoArgs = {
        calculator: { operation: "multiply", a: 6, b: 7 },
        get_weather: { city: "Tokyo" },
        manage_notes: { action: "list" },
        get_datetime: { format: "human" },
      };
      const res = await callTool(toolName, demoArgs[toolName] || {});
      setResult({ type: "tool", name: toolName, data: res.result });
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleReadResource = async (uri) => {
    setResult(null);
    setLoading(true);
    try {
      const res = await readResource(uri);
      setResult({ type: "resource", uri, data: res.content });
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleGetPrompt = async (name) => {
    setResult(null);
    setLoading(true);
    try {
      const demoArgs = {
        summarize: { text: "MCP enables AI models to connect with external tools and data sources.", style: "brief" },
        "code-review": { code: "def add(a, b): return a + b", language: "python" },
        "explain-concept": { concept: "Model Context Protocol", level: "beginner" },
      };
      const res = await getPrompt(name, demoArgs[name] || {});
      setResult({ type: "prompt", name, data: res.messages });
    } catch (err) {
      setResult({ error: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-lg">MCP Explorer</CardTitle>
          <CardDescription>Browse server capabilities</CardDescription>
        </div>
        <Button variant="ghost" size="icon" onClick={refresh} disabled={loading}>
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col min-h-0 gap-3">
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList className="w-full">
            <TabsTrigger value="tools" className="flex-1 gap-1">
              <Wrench className="h-3 w-3" /> Tools ({tools.length})
            </TabsTrigger>
            <TabsTrigger value="resources" className="flex-1 gap-1">
              <FileText className="h-3 w-3" /> Resources ({resources.length})
            </TabsTrigger>
            <TabsTrigger value="prompts" className="flex-1 gap-1">
              <MessageSquare className="h-3 w-3" /> Prompts ({prompts.length})
            </TabsTrigger>
          </TabsList>

          {/* Tools */}
          <TabsContent value="tools">
            <ScrollArea className="max-h-[300px]">
              <div className="space-y-2">
                {tools.map((t) => (
                  <div key={t.name} className="border rounded-md p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{t.name}</span>
                      <Button size="sm" variant="outline" onClick={() => handleCallTool(t.name)}>
                        <Play className="h-3 w-3 mr-1" /> Try
                      </Button>
                    </div>
                    <p className="text-muted-foreground text-xs">{t.description}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Resources */}
          <TabsContent value="resources">
            <ScrollArea className="max-h-[300px]">
              <div className="space-y-2">
                {resources.map((r) => (
                  <div key={r.uri} className="border rounded-md p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{r.name}</span>
                      <Button size="sm" variant="outline" onClick={() => handleReadResource(r.uri)}>
                        <FileText className="h-3 w-3 mr-1" /> Read
                      </Button>
                    </div>
                    <p className="text-muted-foreground text-xs">{r.uri}</p>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Prompts */}
          <TabsContent value="prompts">
            <ScrollArea className="max-h-[300px]">
              <div className="space-y-2">
                {prompts.map((p) => (
                  <div key={p.name} className="border rounded-md p-3 text-sm">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-medium">{p.name}</span>
                      <Button size="sm" variant="outline" onClick={() => handleGetPrompt(p.name)}>
                        <Play className="h-3 w-3 mr-1" /> Try
                      </Button>
                    </div>
                    <p className="text-muted-foreground text-xs">{p.description}</p>
                    {p.arguments?.length > 0 && (
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {p.arguments.map((a) => (
                          <Badge key={a.name} variant="outline" className="text-xs">
                            {a.name}{a.required ? "*" : ""}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>

        {/* Result panel */}
        {result && (
          <div className="border rounded-md p-3 bg-muted/50">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-muted-foreground">
                {result.error ? "Error" : `Result: ${result.name || result.uri}`}
              </span>
              <Button variant="ghost" size="sm" onClick={() => setResult(null)} className="h-6 px-2 text-xs">
                Clear
              </Button>
            </div>
            <pre className="text-xs whitespace-pre-wrap overflow-auto max-h-[200px]">
              {result.error
                ? result.error
                : typeof result.data === "string"
                ? result.data
                : JSON.stringify(result.data, null, 2)}
            </pre>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
