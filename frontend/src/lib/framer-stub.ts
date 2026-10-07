export function useIsStaticRenderer() {
  return false;
}

export function addPropertyControls() {}

export const ControlType = {
  Array: "array",
  Object: "object",
  String: "string",
  Number: "number",
  ResponsiveImage: "image",
  Boolean: "boolean",
  Link: "link",
  Color: "color",
  Enum: "enum",
  Font: "font",
} as const;
