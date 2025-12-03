# MERL-T Frontend Refactoring Plan

**Data**: Novembre 2025
**Versione**: 1.0
**Stato**: PROPOSTA

---

## Executive Summary

Il frontend attuale (~15,000 LOC) è cresciuto organicamente senza una visione chiara dell'utente finale. Questo piano propone un **refactoring completo** focalizzato sulle reali esigenze di MERL-T: **query legali → risposte esperte → feedback RLCF**.

### Problemi Attuali

| Problema | Impatto | Soluzione |
|----------|---------|-----------|
| **Frammentazione UI** | 3 pagine di configurazione AI diverse | Unificare in Settings |
| **Focus RLCF vs Query** | Dashboard mostra task RLCF, non query legali | Ribaltare priorità |
| **Admin sovraccarico** | AdminDashboard con troppe funzioni | Separare in moduli |
| **UX inconsistente** | Stili e pattern diversi tra pagine | Design system unificato |
| **Query flow incompleto** | Monitor esiste ma non integrato | Flusso query → result → feedback |

### Obiettivi del Refactor

1. **User-First**: Interfaccia centrata sulle query legali
2. **Role-Based**: Dashboard diversi per utente/esperto/admin
3. **Minimal & Clean**: Rimuovere complessità non necessaria
4. **Real-Time**: Monitoraggio esecuzione query in tempo reale
5. **Mobile-Ready**: Responsive design per tutti i dispositivi

---

## Analisi Backend API

### API Disponibili (che il frontend DEVE supportare)

#### 1. Orchestration API (porta 8000)

```typescript
// Query Execution
POST /query/execute          → Esegue query legale completa
GET  /query/status/{trace_id} → Stato esecuzione (polling)
GET  /query/history/{user_id} → Storico query utente
GET  /query/retrieve/{trace_id} → Dettagli completi query

// Feedback
POST /feedback/user          → Rating utente (1-5 stelle)
POST /feedback/rlcf          → Correzioni esperto RLCF
POST /feedback/ner           → Correzioni NER
GET  /feedback/stats         → Statistiche feedback
```

#### 2. RLCF API (porta 8001)

```typescript
// Tasks & Users (RLCF Framework)
GET/POST /tasks/*            → Gestione task valutativi
GET/POST /users/*            → Gestione utenti/esperti
GET      /analytics/*        → Metriche sistema
GET/PUT  /config/*           → Configurazione modelli
POST     /ai/generate        → Generazione AI (testing)
```

#### 3. Ingestion API (porta 8002)

```typescript
// Knowledge Graph Ingestion
POST /batch/create           → Crea batch ingestione
GET  /batch/{id}/progress    → Progresso batch
POST /validate/entity        → Validazione entità
```

### Data Models Chiave

```typescript
// Query Request
interface QueryRequest {
  query: string;                    // "È valido un contratto firmato da un minore?"
  context?: {
    temporal_reference?: string;    // "2024-01-01" | "latest"
    jurisdiction?: string;          // "nazionale" | "regionale" | "comunitario"
    user_role?: string;             // "cittadino" | "avvocato" | "giudice"
  };
  options?: {
    max_iterations?: number;        // 1-10
    return_trace?: boolean;         // Include execution trace
    timeout_ms?: number;            // 1000-120000
  };
}

// Query Response
interface QueryResponse {
  trace_id: string;
  answer: {
    primary_answer: string;
    confidence: number;             // 0.0-1.0
    legal_basis: LegalBasis[];      // Norme citate
    jurisprudence?: CaseLaw[];      // Sentenze
    alternative_interpretations?: Alternative[];
    uncertainty_preserved: boolean; // RLCF principle
  };
  execution_trace?: {
    stages_executed: string[];      // ["preprocessing", "routing", "retrieval", "reasoning", "synthesis"]
    experts_consulted: string[];    // ["literal", "systemic", "precedent"]
    total_time_ms: number;
    stage_timings: Record<string, number>;
  };
  metadata: {
    complexity_score: number;
    intent_detected: string;
    concepts_identified: string[];
    entities_identified: Entity[];
  };
}

// Query Status (per polling)
interface QueryStatus {
  trace_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  current_stage?: string;
  progress_percent?: number;
  stage_logs?: string[];
  result?: QueryResponse;
  error?: string;
}
```

---

## Nuova Architettura Frontend

### Struttura Directory

```
frontend/rlcf-web/src/
├── app/
│   ├── routes/
│   │   └── index.tsx              # Route definitions
│   ├── store/
│   │   ├── auth.ts                # Auth state (KEEP)
│   │   └── query.ts               # Query state (KEEP)
│   └── providers/
│       └── app-provider.tsx       # TanStack Query (KEEP)
│
├── components/
│   ├── ui/                        # Base components (KEEP ALL)
│   │   ├── Button.tsx
│   │   ├── Card.tsx
│   │   ├── Badge.tsx
│   │   ├── Modal.tsx
│   │   ├── Progress.tsx
│   │   └── ...
│   ├── layout/                    # NEW: Unified layout
│   │   ├── AppShell.tsx           # Main layout wrapper
│   │   ├── Sidebar.tsx            # Navigation (role-based)
│   │   ├── Header.tsx             # Top bar with user info
│   │   └── Footer.tsx             # Minimal footer
│   └── shared/                    # Shared components
│       ├── AuthGuard.tsx          # (KEEP)
│       ├── ErrorBoundary.tsx      # (KEEP)
│       ├── LoadingSpinner.tsx     # NEW
│       └── EmptyState.tsx         # NEW
│
├── features/
│   ├── query/                     # PRIORITY 1: Core query feature
│   │   ├── QueryPage.tsx          # NEW: Unified query interface
│   │   ├── components/
│   │   │   ├── QueryInput.tsx     # NEW: Simple query input
│   │   │   ├── QueryOptions.tsx   # Context + options (collapsed)
│   │   │   ├── ExecutionProgress.tsx # NEW: Real-time stages
│   │   │   ├── AnswerDisplay.tsx  # KEEP (polish)
│   │   │   ├── LegalBasisList.tsx # KEEP (polish)
│   │   │   ├── ExpertOpinions.tsx # NEW: Multi-expert views
│   │   │   └── FeedbackForm.tsx   # NEW: Unified feedback
│   │   └── hooks/
│   │       └── useQueryExecution.ts # NEW: Query lifecycle
│   │
│   ├── history/                   # PRIORITY 2: Query history
│   │   ├── HistoryPage.tsx        # NEW: Timeline view
│   │   └── components/
│   │       ├── HistoryList.tsx
│   │       └── HistoryFilters.tsx
│   │
│   ├── dashboard/                 # PRIORITY 3: Role-based dashboard
│   │   ├── UserDashboard.tsx      # NEW: For regular users
│   │   ├── ExpertDashboard.tsx    # NEW: For RLCF experts
│   │   └── AdminDashboard.tsx     # REFACTOR: Simplified
│   │
│   ├── admin/                     # PRIORITY 4: Admin features
│   │   ├── settings/
│   │   │   ├── SettingsPage.tsx   # NEW: Unified settings
│   │   │   ├── AIModelsTab.tsx    # Model configuration
│   │   │   ├── SystemTab.tsx      # System settings
│   │   │   └── UsersTab.tsx       # User management
│   │   ├── monitor/
│   │   │   ├── MonitorPage.tsx    # Query monitoring
│   │   │   └── components/
│   │   └── ingestion/             # KEEP (mostly)
│   │       └── IngestionPage.tsx
│   │
│   ├── expert/                    # PRIORITY 5: RLCF expert features
│   │   ├── TasksPage.tsx          # Tasks to review
│   │   ├── ReviewPage.tsx         # Submit corrections
│   │   └── components/
│   │       ├── TaskCard.tsx
│   │       ├── CorrectionForm.tsx
│   │       └── NERCorrectionForm.tsx
│   │
│   └── auth/                      # KEEP
│       └── Login.tsx
│
├── hooks/                         # Custom hooks
│   ├── useOrchestration.ts        # KEEP (polish)
│   └── useApi.ts                  # KEEP
│
├── lib/
│   ├── api.ts                     # KEEP (well structured)
│   └── utils.ts                   # Utility functions
│
└── types/
    ├── index.ts                   # KEEP
    └── orchestration.ts           # KEEP
```

### Route Map

```typescript
const routes = [
  // Public
  { path: "/login", element: <Login /> },

  // Authenticated (all users)
  { path: "/", element: <Navigate to="/query" /> },
  { path: "/query", element: <QueryPage /> },
  { path: "/query/:traceId", element: <QueryPage /> },  // View specific result
  { path: "/history", element: <HistoryPage /> },
  { path: "/profile", element: <ProfilePage /> },

  // Expert only
  { path: "/expert", element: <ExpertDashboard />, roles: ["expert", "admin"] },
  { path: "/expert/tasks", element: <TasksPage />, roles: ["expert", "admin"] },
  { path: "/expert/review/:taskId", element: <ReviewPage />, roles: ["expert", "admin"] },

  // Admin only
  { path: "/admin", element: <AdminDashboard />, roles: ["admin"] },
  { path: "/admin/settings", element: <SettingsPage />, roles: ["admin"] },
  { path: "/admin/monitor", element: <MonitorPage />, roles: ["admin"] },
  { path: "/admin/users", element: <UsersPage />, roles: ["admin"] },
  { path: "/admin/ingestion", element: <IngestionPage />, roles: ["admin"] },
];
```

---

## Componenti Chiave da Sviluppare

### 1. QueryPage (Pagina Principale Query)

```tsx
// features/query/QueryPage.tsx
// Flusso: Input → Esecuzione → Risultati → Feedback (tutto in una pagina)

function QueryPage() {
  const [phase, setPhase] = useState<"input" | "executing" | "result">("input");
  const [traceId, setTraceId] = useState<string | null>(null);

  return (
    <div className="max-w-4xl mx-auto">
      {phase === "input" && (
        <>
          <QueryInput onSubmit={handleSubmit} />
          <Collapsible title="Opzioni Avanzate">
            <QueryOptions />
          </Collapsible>
          <RecentQueries onSelect={loadQuery} />
        </>
      )}

      {phase === "executing" && (
        <ExecutionProgress
          traceId={traceId}
          onComplete={() => setPhase("result")}
        />
      )}

      {phase === "result" && (
        <>
          <AnswerDisplay traceId={traceId} />
          <LegalBasisList traceId={traceId} />
          <ExpertOpinions traceId={traceId} />
          <FeedbackForm traceId={traceId} onNewQuery={() => setPhase("input")} />
        </>
      )}
    </div>
  );
}
```

### 2. ExecutionProgress (Monitoraggio Real-Time)

```tsx
// features/query/components/ExecutionProgress.tsx
// Visualizza stages della pipeline in tempo reale

const STAGES = [
  { id: "preprocessing", label: "Analisi Query", icon: Search },
  { id: "routing", label: "Pianificazione", icon: Route },
  { id: "retrieval", label: "Ricerca Fonti", icon: Database },
  { id: "reasoning", label: "Ragionamento Esperti", icon: Brain },
  { id: "synthesis", label: "Sintesi Risposta", icon: Sparkles },
];

function ExecutionProgress({ traceId, onComplete }) {
  const { data: status, isLoading } = usePollQueryStatus(traceId, {
    refetchInterval: 1000, // Poll ogni secondo
    enabled: !!traceId,
  });

  useEffect(() => {
    if (status?.status === "completed") {
      onComplete();
    }
  }, [status?.status]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Elaborazione in corso...</CardTitle>
        <Progress value={status?.progress_percent || 0} />
      </CardHeader>
      <CardContent>
        <div className="flex justify-between">
          {STAGES.map((stage, i) => (
            <StageIndicator
              key={stage.id}
              stage={stage}
              status={getStageStatus(status, stage.id)}
              isActive={status?.current_stage === stage.id}
            />
          ))}
        </div>

        {/* Log in tempo reale */}
        {status?.stage_logs && (
          <div className="mt-4 p-3 bg-slate-900 rounded text-xs font-mono max-h-32 overflow-y-auto">
            {status.stage_logs.map((log, i) => (
              <div key={i} className="text-slate-400">{log}</div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
```

### 3. AnswerDisplay (Risposta con Provenance)

```tsx
// features/query/components/AnswerDisplay.tsx
// Mostra risposta principale + confidence + fonti

function AnswerDisplay({ traceId }) {
  const { data: result } = useRetrieveQuery(traceId);

  if (!result) return <LoadingSpinner />;

  const { answer, metadata } = result;

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader>
        <div className="flex justify-between items-start">
          <CardTitle>Risposta</CardTitle>
          <ConfidenceBadge score={answer.confidence} />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Risposta principale */}
        <div className="prose prose-invert max-w-none">
          <ReactMarkdown>{answer.primary_answer}</ReactMarkdown>
        </div>

        {/* Alert se c'è incertezza */}
        {answer.uncertainty_preserved && (
          <Alert variant="warning">
            <AlertTriangle className="w-4 h-4" />
            <span>
              Gli esperti non hanno raggiunto un consenso unanime.
              Vedi le interpretazioni alternative sotto.
            </span>
          </Alert>
        )}

        {/* Metadata collapsible */}
        <Collapsible title={`${metadata.concepts_identified.length} concetti identificati`}>
          <div className="flex flex-wrap gap-2">
            {metadata.concepts_identified.map(concept => (
              <Badge key={concept} variant="outline">{concept}</Badge>
            ))}
          </div>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
```

### 4. Unified Settings Page

```tsx
// features/admin/settings/SettingsPage.tsx
// Tutte le configurazioni in un'unica pagina con tabs

function SettingsPage() {
  const [activeTab, setActiveTab] = useState("models");

  const tabs = [
    { id: "models", label: "AI Models", icon: Cpu },
    { id: "system", label: "Sistema", icon: Settings },
    { id: "users", label: "Utenti", icon: Users },
    { id: "api", label: "API Keys", icon: Key },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Impostazioni</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {tabs.map(tab => (
            <TabsTrigger key={tab.id} value={tab.id}>
              <tab.icon className="w-4 h-4 mr-2" />
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="models">
          <AIModelsSettings />
        </TabsContent>
        <TabsContent value="system">
          <SystemSettings />
        </TabsContent>
        <TabsContent value="users">
          <UsersSettings />
        </TabsContent>
        <TabsContent value="api">
          <APIKeysSettings />
        </TabsContent>
      </Tabs>
    </div>
  );
}
```

---

## Componenti da MANTENERE (con polish)

| File | Motivazione | Modifiche Necessarie |
|------|-------------|---------------------|
| `components/ui/*` | Base UI solida | Nessuna |
| `lib/api.ts` | API client ben strutturato | Nessuna |
| `hooks/useOrchestration.ts` | Hook per orchestration | Polish |
| `features/query/components/LegalBasisPanel.tsx` | Visualizza fonti legali | Rinominare + Polish |
| `features/query/components/JurisprudencePanel.tsx` | Visualizza sentenze | Polish |
| `features/orchestration/ExecutionTraceViewer.tsx` | Trace dettagliato | Semplificare |
| `features/orchestration/components/ExpertOpinionPanel.tsx` | Opinioni esperti | Integrare in QueryPage |
| `features/admin/IngestionManager/*` | KG ingestion | Mantenere separato |
| `features/auth/Login.tsx` | Autenticazione | Mantenere |
| `app/store/*` | Zustand stores | Mantenere |

## Componenti da ELIMINARE

| File | Motivazione |
|------|-------------|
| `features/admin/AIConfiguration.tsx` | Sostituito da SettingsPage |
| `features/admin/ConfigurationManager.tsx` | Troppo complesso, sostituito |
| `features/admin/AIModelsConfig.tsx` | Duplicato, integrare in Settings |
| `features/dashboard/Dashboard.tsx` | Rifatto come role-based |
| `features/evaluation/*` | RLCF-specific, spostare in /expert |
| `features/analytics/*` | Troppo dettagliato, semplificare |

---

## Piano di Implementazione

### Fase 1: Setup & Cleanup (2-3 giorni)

1. **Creare struttura directory nuova**
2. **Spostare componenti UI in posto**
3. **Creare nuovo AppShell layout**
4. **Rimuovere componenti duplicati**

### Fase 2: Query Flow (3-4 giorni)

1. **QueryPage unificata**
   - QueryInput semplice
   - ExecutionProgress real-time
   - AnswerDisplay con confidence
   - LegalBasisList
   - FeedbackForm integrato

2. **History Page**
   - Timeline delle query
   - Filtri e ricerca
   - Quick actions

### Fase 3: Admin Features (2-3 giorni)

1. **SettingsPage unificata**
   - AI Models (input text libero!)
   - System settings
   - User management
   - API keys

2. **MonitorPage**
   - Query monitoring dashboard
   - Metriche in tempo reale

### Fase 4: Expert Features (2-3 giorni)

1. **ExpertDashboard**
   - Task RLCF assegnati
   - Statistiche personali

2. **ReviewPage**
   - Form correzioni
   - NER corrections

### Fase 5: Polish & Testing (2-3 giorni)

1. **Responsive design**
2. **Error handling**
3. **Loading states**
4. **E2E testing**

---

## Design Guidelines

### Color Palette

```css
/* Primary */
--purple-500: #8b5cf6;   /* Accent principale */
--blue-500: #3b82f6;     /* Links, info */

/* Status */
--green-500: #22c55e;    /* Success, completed */
--yellow-500: #eab308;   /* Warning, processing */
--red-500: #ef4444;      /* Error, failed */

/* Neutral */
--slate-950: #020617;    /* Background */
--slate-900: #0f172a;    /* Cards */
--slate-400: #94a3b8;    /* Text secondary */
--white: #ffffff;        /* Text primary */
```

### Typography

```css
/* Headings */
h1: 2rem (32px), font-bold
h2: 1.5rem (24px), font-semibold
h3: 1.25rem (20px), font-medium

/* Body */
body: 1rem (16px), font-normal
small: 0.875rem (14px)
xs: 0.75rem (12px)

/* Font Family */
font-family: 'Inter', system-ui, sans-serif;
font-mono: 'JetBrains Mono', monospace;
```

### Spacing

```css
/* Consistent spacing scale */
--space-1: 0.25rem;   /* 4px */
--space-2: 0.5rem;    /* 8px */
--space-3: 0.75rem;   /* 12px */
--space-4: 1rem;      /* 16px */
--space-6: 1.5rem;    /* 24px */
--space-8: 2rem;      /* 32px */
--space-12: 3rem;     /* 48px */
```

### Component Patterns

```tsx
// Card pattern
<Card className="border-slate-700">
  <CardHeader>
    <CardTitle>Title</CardTitle>
    <CardDescription>Description</CardDescription>
  </CardHeader>
  <CardContent>
    {/* Content */}
  </CardContent>
  <CardFooter>
    <Button>Action</Button>
  </CardFooter>
</Card>

// Form pattern
<form onSubmit={handleSubmit}>
  <div className="space-y-4">
    <div>
      <Label htmlFor="field">Field Label</Label>
      <Input id="field" {...register("field")} />
      {errors.field && <p className="text-red-500 text-sm">{errors.field.message}</p>}
    </div>
  </div>
  <Button type="submit">Submit</Button>
</form>

// Loading pattern
{isLoading ? (
  <LoadingSpinner />
) : error ? (
  <ErrorMessage error={error} />
) : (
  <Content data={data} />
)}
```

---

## Metriche di Successo

| Metrica | Attuale | Target |
|---------|---------|--------|
| Bundle size | ~500KB | <300KB |
| First Contentful Paint | ~2s | <1s |
| Time to Interactive | ~3s | <2s |
| Lighthouse Score | ~70 | >90 |
| LOC Frontend | ~15,000 | <10,000 |
| Componenti duplicati | 3+ | 0 |
| User journey steps (query) | 4+ clicks | 2 clicks |

---

## Rischi e Mitigazioni

| Rischio | Impatto | Mitigazione |
|---------|---------|-------------|
| Breaking changes API | Alto | Verificare compatibilità prima |
| Perdita funzionalità | Medio | Audit completo pre-refactor |
| Tempi lunghi | Medio | Fasi incrementali, deploy graduale |
| Regressioni | Medio | Test E2E prima di merge |

---

## Prossimi Passi

1. **Approvazione**: Revisione piano con stakeholder
2. **Branch**: Creare `feature/frontend-refactor`
3. **Fase 1**: Iniziare con cleanup e struttura
4. **Review**: Code review dopo ogni fase
5. **Deploy**: Merge progressivo su develop

---

**Autore**: Claude AI Assistant
**Revisione**: Da confermare
