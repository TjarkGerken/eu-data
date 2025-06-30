import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { motion } from "framer-motion";

interface KpiShowcaseBlockProps {
  block: {
    title?: string;
    description?: string;
    kpis: Array<{
      title: string;
      value: string;
      unit?: string;
      trend?: "up" | "down" | "stable";
      changeValue?: string;
      color?: string;
    }>;
    references?: Array<{
      id: string;
      title: string;
      authors: string[];
      type: string;
    }>;
  };
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
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {block.kpis?.map((kpi, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="text-center">
              <CardHeader>
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-3xl font-bold ${kpi.color || 'text-[#2d5a3d]'}`}>
                  {kpi.value}
                  {kpi.unit && <span className="text-sm ml-1">{kpi.unit}</span>}
                </div>
                {kpi.changeValue && (
                  <div className={`text-sm mt-2 ${
                    kpi.trend === 'up' ? 'text-green-600' : 
                    kpi.trend === 'down' ? 'text-red-600' : 
                    'text-gray-600'
                  }`}>
                    {kpi.changeValue}
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {block.references && block.references.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.3 }}
          className="mt-8 pt-6 border-t border-muted"
        >
          <h4 className="text-sm font-semibold text-muted-foreground mb-3">References</h4>
          <div className="space-y-2">
            {block.references.map((ref) => (
              <div 
                key={ref.id} 
                className="text-xs text-muted-foreground cursor-pointer hover:text-foreground transition-colors"
                onClick={() => {
                  const event = new CustomEvent('highlightReference', { detail: ref.id });
                  window.dispatchEvent(event);
                }}
              >
                <span className="font-medium">{ref.title}</span>
                {ref.authors && ref.authors.length > 0 && (
                  <span className="ml-2">- {ref.authors.join(", ")}</span>
                )}
              </div>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}
