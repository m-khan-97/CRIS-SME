import { lazy, Suspense } from "react";
import App from "./App";
import { AssessmentProvider } from "./context/AssessmentContext";
import { enterpriseMode } from "./enterprise/config";

const EnterpriseApp = lazy(() => import("./enterprise/App"));
export function ConsoleRoot() {
  return enterpriseMode ? <Suspense fallback={<p>Loading enterprise console...</p>}><EnterpriseApp /></Suspense>
    : <AssessmentProvider><App /></AssessmentProvider>;
}
