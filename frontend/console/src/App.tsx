import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { Spinner } from "./components/ui";

const Overview = lazy(() => import("./pages/Overview").then((m) => ({ default: m.Overview })));
const NewAssessment = lazy(() =>
  import("./pages/NewAssessment").then((m) => ({ default: m.NewAssessment }))
);
const Findings = lazy(() => import("./pages/Findings").then((m) => ({ default: m.Findings })));
const Resources = lazy(() => import("./pages/Resources").then((m) => ({ default: m.Resources })));
const Compliance = lazy(() =>
  import("./pages/Compliance").then((m) => ({ default: m.Compliance }))
);
const PublicExposure = lazy(() =>
  import("./pages/PublicExposure").then((m) => ({ default: m.PublicExposure }))
);
const AttackPaths = lazy(() =>
  import("./pages/AttackPaths").then((m) => ({ default: m.AttackPaths }))
);
const Personas = lazy(() => import("./pages/Personas").then((m) => ({ default: m.Personas })));
const TrustCenter = lazy(() =>
  import("./pages/TrustCenter").then((m) => ({ default: m.TrustCenter }))
);
const Remediation = lazy(() =>
  import("./pages/Remediation").then((m) => ({ default: m.Remediation }))
);
const EvidenceProvenance = lazy(() =>
  import("./pages/EvidenceProvenance").then((m) => ({ default: m.EvidenceProvenance }))
);
const CyberEssentials = lazy(() =>
  import("./pages/CyberEssentials").then((m) => ({ default: m.CyberEssentials }))
);
const HealthcareIot = lazy(() =>
  import("./pages/HealthcareIot").then((m) => ({ default: m.HealthcareIot }))
);
const DisclosureRoom = lazy(() =>
  import("./pages/DisclosureRoom").then((m) => ({ default: m.DisclosureRoom }))
);
const ReportsArtifacts = lazy(() =>
  import("./pages/ReportsArtifacts").then((m) => ({ default: m.ReportsArtifacts }))
);
const TrendHistory = lazy(() =>
  import("./pages/TrendHistory").then((m) => ({ default: m.TrendHistory }))
);
const Governance = lazy(() =>
  import("./pages/Governance").then((m) => ({ default: m.Governance }))
);
const NativeValidation = lazy(() =>
  import("./pages/NativeValidation").then((m) => ({ default: m.NativeValidation }))
);

function RouteFallback() {
  return (
    <div className="flex h-full items-center justify-center gap-2 p-8 text-text-muted">
      <Spinner /> Loading…
    </div>
  );
}

function App() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Overview />} />
          <Route path="assessment" element={<NewAssessment />} />
          <Route path="findings" element={<Findings />} />
          <Route path="resources" element={<Resources />} />
          <Route path="attack-paths" element={<AttackPaths />} />
          <Route path="personas" element={<Personas />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="cyber-essentials" element={<CyberEssentials />} />
          <Route path="iomt" element={<HealthcareIot />} />
          <Route path="remediation" element={<Remediation />} />
          <Route path="evidence" element={<EvidenceProvenance />} />
          <Route path="trust" element={<TrustCenter />} />
          <Route path="disclosure" element={<DisclosureRoom />} />
          <Route path="reports" element={<ReportsArtifacts />} />
          <Route path="trend" element={<TrendHistory />} />
          <Route path="governance" element={<Governance />} />
          <Route path="native-validation" element={<NativeValidation />} />
          <Route path="public-exposure" element={<PublicExposure />} />
        </Route>
      </Routes>
    </Suspense>
  );
}

export default App;
