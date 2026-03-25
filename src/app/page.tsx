import { ScreenerForm } from "@/components/ScreenerForm";

export default function Home() {
  return (
    <main className="flex-1">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold tracking-tight">
            Magic Formula Screener
          </h1>
          <p className="mt-3 text-lg text-gray-500 dark:text-gray-400 max-w-xl mx-auto">
            Find good companies at cheap prices using Joel Greenblatt&apos;s
            Magic Formula — ranking stocks by earnings yield and return on capital.
          </p>
        </div>

        <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6 shadow-sm">
          <ScreenerForm />
        </div>

        <div className="mt-8 text-xs text-gray-400 text-center space-y-1">
          <p>
            Based on &ldquo;The Little Book That Beats the Market&rdquo; by Joel Greenblatt.
          </p>
          <p>
            This screener produces educational analysis, not investment advice.
            Consult a licensed financial advisor before making investment decisions.
          </p>
        </div>
      </div>
    </main>
  );
}
