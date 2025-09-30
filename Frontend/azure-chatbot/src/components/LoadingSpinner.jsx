import { ProgressSpinner } from "primereact/progressspinner";

export default function LoadingSpinner() {
  return (
    <div
      className="
				flex 
				h-full
				w-full
				items-center 
				justify-center
				self-center
				bg-transparent
				rounded-full
				px-3 py-2
				mb-2">
      <ProgressSpinner fill="transparent" animationDuration="1s" />
    </div>
  );
}
