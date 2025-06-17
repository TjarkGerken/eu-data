import { ClimateTimelineMinimalBlock } from "@/lib/types";
import { ClimateTimelineMinimal } from "@/components/motion-blocks/climate-timeline-minimal";

interface ClimateTimelineMinimalBlockProps {
  block: ClimateTimelineMinimalBlock;
}

export default function ClimateTimelineMinimalBlockComponent({
  block,
}: ClimateTimelineMinimalBlockProps) {
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
      <ClimateTimelineMinimal />
    </div>
  );
}
