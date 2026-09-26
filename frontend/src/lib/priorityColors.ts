/**
 * Priority-band colors for map choropleth and ranking badges.
 */

export type PriorityBand = "low" | "medium" | "high" | string;

export function priorityFill(band: PriorityBand): string {
  switch (band) {
    case "high":
      return "#d4655a";
    case "medium":
      return "#e0a84a";
    case "low":
      return "#4aa3d9";
    default:
      return "#8ab4cf";
  }
}

export function priorityStroke(band: PriorityBand): string {
  switch (band) {
    case "high":
      return "#a84840";
    case "medium":
      return "#b07e28";
    case "low":
      return "#2f7fb8";
    default:
      return "#5a7a8f";
  }
}
