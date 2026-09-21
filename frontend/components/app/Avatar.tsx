import { getInitial, getAvatarColor } from "@/lib/utils";

interface AvatarProps {
  email: string;
  size?: number;
}

export function Avatar({ email, size = 28 }: AvatarProps) {
  const color = getAvatarColor(email);
  const initial = getInitial(email);
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: color + "20",
        border: "1px solid " + color + "40",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size * 0.38,
        fontWeight: 700,
        color: color,
        flexShrink: 0,
        fontFamily: "Syne, sans-serif",
      }}
    >
      {initial}
    </div>
  );
}
