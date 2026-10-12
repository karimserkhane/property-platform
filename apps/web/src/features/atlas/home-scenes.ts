// Editorial photographs of Abu Dhabi; these are not project or cadastral evidence.
export const HOME_SCENES = [
  {
    key: "night",
    image: "abu-dhabi-night",
    height: 1235,
    photographer: "Kevin JD",
    url: "https://unsplash.com/photos/city-skyline-during-night-time-S5SQzWdUhoE",
    position: "62% 64%",
  },
  {
    key: "coast",
    image: "abu-dhabi-coast",
    height: 1440,
    photographer: "Hanks K",
    url: "https://unsplash.com/photos/beach-palm-trees-and-resort-under-a-hazy-sky-_c08bbHy-xg",
    position: "50% 74%",
  },
  {
    key: "sunset",
    image: "abu-dhabi-sunset",
    height: 1280,
    photographer: "Yulia Evtushenko",
    url: "https://unsplash.com/photos/a-couple-of-palm-trees-sitting-next-to-each-other-MhpX3VgaG4U",
    position: "66% 58%",
  },
] as const;

export type GalleryLabels = Record<
  | "galleryLabel"
  | "photoCredit"
  | "night"
  | "coast"
  | "sunset"
  | "pause"
  | "play",
  string
>;
