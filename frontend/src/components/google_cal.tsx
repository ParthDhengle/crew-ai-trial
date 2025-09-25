import React from "react";

type Props = {
  calendarId?: string; // e.g. "primary" or "your.email@gmail.com"
  mode?: "WEEK" | "MONTH" | "AGENDA";
  timezone?: string;
  width?: number | string;
  height?: number | string;
};

export default function GoogleCalendarEmbed({
  calendarId = "parthdhengle12@gmail.com",
  mode = "WEEK",
  timezone = "Asia/Kolkata",
  width = "100%",
  height = "100%",
}: Props) {
  // make sure calendarId is URL-encoded (emails contain @ -> %40)
  const encodedCalendarId = encodeURIComponent(calendarId);

  const params = new URLSearchParams({
    src: encodedCalendarId,
    ctz: timezone,
    mode,
    showTitle: "1",
    showNav: "1",
    showDate: "1",
    showTabs: "1",
    showCalendars: "1",
    showTz: "0",
  });

  const src="https://calendar.google.com/calendar/embed?src=parthdhengle2004%40gmail.com&ctz=Asia%2FKolkata";

  return (
    <iframe
      title="Google Calendar"
      src={src}
      style={{
        border: "0",               // React.CSSProperties — string
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
      }}
      frameBorder={0}
      // scrolling is not strictly recommended in JSX, but you can set it as below:
      // scrolling="no"
      // allowFullScreen if you want:
      // allowFullScreen
    />
  );
}
