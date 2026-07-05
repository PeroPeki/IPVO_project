import { G, Rect, Text as SvgText } from 'react-native-svg';
import { Colors } from '../constants/colors';

export type FloorTable = {
  id: string;
  label: string;
  type: string;
  x: number; y: number; width: number; height: number;
  capacity: number;
  min_spend: number;
  deposit: number;
  section_id: string | null;
  description?: string;
  is_available?: boolean;
  reservation_status?: string | null;
};

/**
 * Jedan stol na SVG mapi:
 * - slobodan: zeleni rub, može se kliknuti
 * - rezerviran: crveni rub, ne može se kliknuti
 */
export default function TableMarker({
  table, onPress,
}: {
  table: FloorTable;
  onPress: (table: FloorTable) => void;
}) {
  const available = table.is_available !== false;
  const stroke = available ? Colors.success : Colors.error;

  return (
    <G onPress={available ? () => onPress(table) : undefined}>
      <Rect
        x={table.x - table.width / 2}
        y={table.y - table.height / 2}
        width={table.width}
        height={table.height}
        rx={1.2}
        fill={table.type === 'vip_separe' ? Colors.accent2 : Colors.accent3}
        fillOpacity={available ? 0.85 : 0.35}
        stroke={stroke}
        strokeWidth={0.5}
      />
      <SvgText
        x={table.x}
        y={table.y + 1}
        textAnchor="middle"
        fontSize={2.6}
        fill={Colors.textLight}
        fontWeight="bold"
      >
        {table.label}
      </SvgText>
    </G>
  );
}
