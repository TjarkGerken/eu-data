import { NeuralClimateNetworkBlock } from "@/lib/types";
import { NeuralClimateNetwork } from "@/components/motion-blocks/neural-climate-network";

interface NeuralClimateNetworkBlockProps {
  block: NeuralClimateNetworkBlock;
}

export default function NeuralClimateNetworkBlockComponent({
  block,
}: NeuralClimateNetworkBlockProps) {
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
      <NeuralClimateNetwork />
    </div>
  );
}
