export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

export interface ContentBlockFormData {
  story_id: string;
  block_type: string;
  title: string;
  content: string;
  data: any;
  language: "en" | "de";
  order_index: number;
  selectedReferences?: string[];
}

const REQUIRED_FIELDS = {
  story_id: "Story ID is required",
  block_type: "Block type is required",
  language: "Language is required",
  order_index: "Order index is required",
};

const BLOCK_TYPES = [
  "visualization",
  "callout",
  "statistics",
  "markdown",
  "timeline",
  "quote",
  "climate-timeline",
  "animated-quote",
  "climate-dashboard",
  "temperature-spiral",
  "animated-statistics",
  "interactive-callout",
  "neural-climate-network",
  "earth-pulse",
  "impact-comparison",
  "kpi-showcase",
  "climate-metamorphosis",
  "climate-timeline-minimal",
  "data-storm",
  "carbon-molecule-dance",
  "climate-infographic",
];

export function validateContentBlock(
  formData: ContentBlockFormData
): ValidationResult {
  const errors: ValidationError[] = [];

  Object.entries(REQUIRED_FIELDS).forEach(([field, message]) => {
    const value = formData[field as keyof ContentBlockFormData];
    if (!value || (typeof value === "string" && value.trim() === "")) {
      errors.push({ field, message });
    }
  });

  if (formData.story_id && formData.story_id.trim().length < 3) {
    errors.push({
      field: "story_id",
      message: "Story ID must be at least 3 characters long",
    });
  }

  if (formData.block_type && !BLOCK_TYPES.includes(formData.block_type)) {
    errors.push({
      field: "block_type",
      message: "Invalid block type selected",
    });
  }

  if (formData.order_index < 0) {
    errors.push({
      field: "order_index",
      message: "Order index must be 0 or greater",
    });
  }

  if (formData.data) {
    try {
      if (typeof formData.data === "string") {
        JSON.parse(formData.data);
      }
    } catch {
      errors.push({
        field: "data",
        message: "Data must be valid JSON",
      });
    }
  }

  if (formData.title && formData.title.length > 200) {
    errors.push({
      field: "title",
      message: "Title must be 200 characters or less",
    });
  }

  if (formData.content && formData.content.length > 5000) {
    errors.push({
      field: "content",
      message: "Content must be 5000 characters or less",
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

export function getFieldError(
  errors: ValidationError[],
  fieldName: string
): string | undefined {
  return errors.find((error) => error.field === fieldName)?.message;
}

export function hasFieldError(
  errors: ValidationError[],
  fieldName: string
): boolean {
  return errors.some((error) => error.field === fieldName);
}
