import { KpiShowcaseBlock } from "@/lib/types";
import { KPIShowcase } from "@/components/motion-blocks/kpi-showcase";

interface KpiShowcaseBlockProps {
  block: KpiShowcaseBlock;
}

export default function KpiShowcaseBlockComponent({
  block,
}: KpiShowcaseBlockProps) {
  return (
    <div className="my-8">
      {block.title && (
        <h3 className="text-2xl font-bold mb-4 text-[#2d5a3d]">
          {block.title}
        </h3>
      )}
      {block.description && (
        <p className="text-lg mb-6 text-gray-700">{block.description}</p>
      )}
      <KPIShowcase />
    </div>
  );
}
