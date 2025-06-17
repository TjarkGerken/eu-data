import { ImpactComparisonBlock } from "@/lib/types";
import { ImpactComparison } from "@/components/motion-blocks/impact-comparison";

interface ImpactComparisonBlockProps {
  block: ImpactComparisonBlock;
}

export default function ImpactComparisonBlockComponent({
  block,
}: ImpactComparisonBlockProps) {
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
      <ImpactComparison />
    </div>
  );
}
