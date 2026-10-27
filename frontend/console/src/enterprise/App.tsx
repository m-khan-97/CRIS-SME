import { EnterpriseAuth } from "./Auth";
import { Workspace } from "./Workspace";
import "./enterprise.css";

export default function EnterpriseApp() {
  return <EnterpriseAuth><Workspace /></EnterpriseAuth>;
}
