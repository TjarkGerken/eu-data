import { DataStormBlock } from "@/lib/types";
import { DataStorm } from "@/components/motion-blocks/data-storm";

interface DataStormBlockProps {
  block: DataStormBlock;
}

export default function DataStormBlockComponent({
  block,
}: DataStormBlockProps) {
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
      <DataStorm />
    </div>
  );
}
