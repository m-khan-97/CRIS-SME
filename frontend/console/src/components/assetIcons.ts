import {
  Boxes,
  Database,
  Eye,
  HardDrive,
  KeyRound,
  Network,
  Server,
  Users,
  type LucideIcon,
} from "lucide-react";

const TYPE_ICONS: { match: RegExp; icon: LucideIcon }[] = [
  { match: /storage|data/i, icon: Database },
  { match: /tenant/i, icon: Boxes },
  { match: /identity/i, icon: Users },
  { match: /monitoring/i, icon: Eye },
  { match: /vm|virtualmachine|compute/i, icon: Server },
  { match: /network|nsg|vnet|subnet/i, icon: Network },
  { match: /vault|key/i, icon: KeyRound },
  { match: /disk/i, icon: HardDrive },
];

export function iconForAssetType(assetType: string): LucideIcon {
  const match = TYPE_ICONS.find((entry) => entry.match.test(assetType));
  return match?.icon ?? Boxes;
}
