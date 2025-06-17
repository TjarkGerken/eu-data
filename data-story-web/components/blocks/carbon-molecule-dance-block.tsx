import { CarbonMoleculeDanceBlock } from "@/lib/types";
import { CarbonMoleculeDance } from "@/components/motion-blocks/carbon-molecule-dance";

interface CarbonMoleculeDanceBlockProps {
  block: CarbonMoleculeDanceBlock;
}

export default function CarbonMoleculeDanceBlockComponent({
  block,
}: CarbonMoleculeDanceBlockProps) {
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
      <CarbonMoleculeDance />
    </div>
  );
}
