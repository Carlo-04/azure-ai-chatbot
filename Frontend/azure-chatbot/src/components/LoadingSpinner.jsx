import { ProgressSpinner } from "primereact/progressspinner";

export default function LoadingSpinner() {
  return (
    <div
      className="
				flex 
				h-15
				w-15
				items-center 
				justify-start 
				self-start 
				bg-transparent
				rounded-full
				px-3 py-2
				mb-2">
      <ProgressSpinner fill="transparent" animationDuration="1s" />
    </div>
  );
}
