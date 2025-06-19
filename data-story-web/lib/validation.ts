export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

export interface ContentBlockFormData {
  story_id?: string;
  block_type: string;
  title: string;
  content: string;
  data: any;
  language: "en" | "de";
  order_index: number;
  selectedReferences?: string[];
}

const REQUIRED_FIELDS = {
  block_type: "Block type is required",
  language: "Language is required",
  order_index: "Order index is required",
};

const BLOCK_TYPES = [
  "markdown",
  "callout",
  "visualization",
  "animated-quote",
  "animated-statistics",
  "climate-timeline",
  "climate-dashboard",
  "temperature-spiral",
  "interactive-callout",
  "impact-comparison",
  "kpi-showcase",
  "climate-timeline-minimal",
  "climate-infographic",
  "interactive-map",
];

const CALLOUT_VARIANTS = ["success", "warning", "info", "error"];
const VISUALIZATION_TYPES = ["map", "chart", "trend", "gauge"];
const IMAGE_CATEGORIES = ["exposition", "hazard", "risk", "combined"];
const IMAGE_SCENARIOS = ["current", "severe"];

const validateColorCode = (color: string): boolean => {
  return /^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color);
};

const validateNumberRange = (
  value: number,
  min: number,
  max: number
): boolean => {
  return value >= min && value <= max;
};

const validateBlockSpecificFields = (
  formData: ContentBlockFormData
): ValidationError[] => {
  const errors: ValidationError[] = [];
  const { block_type, data } = formData;

  switch (block_type) {
    case "callout":
      if (!data?.variant || !CALLOUT_VARIANTS.includes(data.variant)) {
        errors.push({
          field: "data.variant",
          message:
            "Valid callout variant is required (success, warning, info, error)",
        });
      }
      break;

    case "animated-quote":
      if (!data?.text?.trim()) {
        errors.push({ field: "data.text", message: "Quote text is required" });
      }
      if (!data?.author?.trim()) {
        errors.push({ field: "data.author", message: "Author is required" });
      }
      break;

    case "animated-statistics":
      if (
        !data?.stats ||
        !Array.isArray(data.stats) ||
        data.stats.length === 0
      ) {
        errors.push({
          field: "data.stats",
          message: "At least one statistic is required",
        });
      } else {
        data.stats.forEach((stat: any, index: number) => {
          if (!stat?.label?.trim()) {
            errors.push({
              field: `data.stats.${index}.label`,
              message: `Statistic ${index + 1} label is required`,
            });
          }
          if (!stat?.value?.trim()) {
            errors.push({
              field: `data.stats.${index}.value`,
              message: `Statistic ${index + 1} value is required`,
            });
          }
          if (stat?.color && !validateColorCode(stat.color)) {
            errors.push({
              field: `data.stats.${index}.color`,
              message: `Statistic ${index + 1} color must be a valid hex code`,
            });
          }
        });
      }
      break;

    case "climate-timeline":
      if (
        !data?.events ||
        !Array.isArray(data.events) ||
        data.events.length === 0
      ) {
        errors.push({
          field: "data.events",
          message: "At least one timeline event is required",
        });
      } else {
        data.events.forEach((event: any, index: number) => {
          if (!event?.year || !validateNumberRange(event.year, 1850, 2100)) {
            errors.push({
              field: `data.events.${index}.year`,
              message: `Event ${index + 1} year must be between 1850 and 2100`,
            });
          }
          if (!event?.title?.trim()) {
            errors.push({
              field: `data.events.${index}.title`,
              message: `Event ${index + 1} title is required`,
            });
          }
          if (event?.color && !validateColorCode(event.color)) {
            errors.push({
              field: `data.events.${index}.color`,
              message: `Event ${index + 1} color must be a valid hex code`,
            });
          }
        });
      }
      break;

    case "climate-dashboard":
      if (
        !data?.metrics ||
        !Array.isArray(data.metrics) ||
        data.metrics.length === 0
      ) {
        errors.push({
          field: "data.metrics",
          message: "At least one metric is required",
        });
      } else {
        data.metrics.forEach((metric: any, index: number) => {
          if (!metric?.title?.trim()) {
            errors.push({
              field: `data.metrics.${index}.title`,
              message: `Metric ${index + 1} title is required`,
            });
          }
          if (!metric?.value?.trim()) {
            errors.push({
              field: `data.metrics.${index}.value`,
              message: `Metric ${index + 1} value is required`,
            });
          }
          if (
            metric?.progress !== undefined &&
            !validateNumberRange(metric.progress, 0, 100)
          ) {
            errors.push({
              field: `data.metrics.${index}.progress`,
              message: `Metric ${index + 1} progress must be between 0 and 100`,
            });
          }
        });
      }
      break;

    case "temperature-spiral":
      if (data?.startYear && !validateNumberRange(data.startYear, 1850, 2100)) {
        errors.push({
          field: "data.startYear",
          message: "Start year must be between 1850 and 2100",
        });
      }
      if (data?.endYear && !validateNumberRange(data.endYear, 1850, 2100)) {
        errors.push({
          field: "data.endYear",
          message: "End year must be between 1850 and 2100",
        });
      }
      if (data?.startYear && data?.endYear && data.startYear >= data.endYear) {
        errors.push({
          field: "data.endYear",
          message: "End year must be after start year",
        });
      }
      if (data?.rotations && !validateNumberRange(data.rotations, 1, 20)) {
        errors.push({
          field: "data.rotations",
          message: "Rotations must be between 1 and 20",
        });
      }
      break;

    case "interactive-callout":
      if (!data?.variant || !CALLOUT_VARIANTS.includes(data.variant)) {
        errors.push({
          field: "data.variant",
          message:
            "Valid callout variant is required (success, warning, info, error)",
        });
      }
      break;

    case "visualization":
      if (!data?.type || !VISUALIZATION_TYPES.includes(data.type)) {
        errors.push({
          field: "data.type",
          message:
            "Valid visualization type is required (map, chart, trend, gauge)",
        });
      }
      if (
        data?.imageCategory &&
        !IMAGE_CATEGORIES.includes(data.imageCategory)
      ) {
        errors.push({
          field: "data.imageCategory",
          message:
            "Valid image category is required (exposition, hazard, risk, combined)",
        });
      }
      if (
        data?.imageScenario &&
        !IMAGE_SCENARIOS.includes(data.imageScenario)
      ) {
        errors.push({
          field: "data.imageScenario",
          message: "Valid image scenario is required (current, severe)",
        });
      }
      break;

    case "climate-timeline-minimal":
      if (
        !data?.events ||
        !Array.isArray(data.events) ||
        data.events.length === 0
      ) {
        errors.push({
          field: "data.events",
          message: "At least one timeline event is required",
        });
      } else {
        data.events.forEach((event: any, index: number) => {
          if (!event?.year || !validateNumberRange(event.year, 1850, 2100)) {
            errors.push({
              field: `data.events.${index}.year`,
              message: `Event ${index + 1} year must be between 1850 and 2100`,
            });
          }
          if (!event?.title?.trim()) {
            errors.push({
              field: `data.events.${index}.title`,
              message: `Event ${index + 1} title is required`,
            });
          }
        });
      }
      break;

    case "markdown":
      if (!formData.content?.trim()) {
        errors.push({
          field: "content",
          message: "Markdown content is required",
        });
      }
      break;
  }

  return errors;
};

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

  const blockSpecificErrors = validateBlockSpecificFields(formData);
  errors.push(...blockSpecificErrors);

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

export const getDefaultBlockData = (blockType: string): any => {
  switch (blockType) {
    case "callout":
    case "interactive-callout":
      return { variant: "info" };
    case "animated-quote":
      return { text: "", author: "", role: "" };
    case "animated-statistics":
      return {
        stats: [
          { icon: "", value: "", label: "", color: "#2d5a3d", trend: "up" },
        ],
      };
    case "climate-timeline":
      return {
        events: [
          {
            year: 2024,
            title: "",
            description: "",
            type: "temperature",
            icon: "",
            color: "#2d5a3d",
          },
        ],
      };
    case "climate-dashboard":
      return {
        metrics: [
          {
            title: "",
            value: "",
            change: "",
            trend: "up",
            status: "success",
            progress: 50,
            target: "",
            description: "",
          },
        ],
      };
    case "temperature-spiral":
      return { startYear: 1880, endYear: 2030, rotations: 8 };
    case "visualization":
      return { type: "chart", imageCategory: "risk" };
    case "climate-timeline-minimal":
      return {
        events: [{ year: 2024, title: "", description: "" }],
      };
    default:
      return {};
  }
};
