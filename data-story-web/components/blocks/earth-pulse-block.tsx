import { EarthPulseBlock } from "@/lib/types";
import { EarthPulse } from "@/components/motion-blocks/earth-pulse";

interface EarthPulseBlockProps {
  block: EarthPulseBlock;
}

export default function EarthPulseBlockComponent({
  block,
}: EarthPulseBlockProps) {
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
      <EarthPulse />
    </div>
  );
}
