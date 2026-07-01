// Side-effect import: registers the Chart.js building blocks used by every
// react-chartjs-2 chart in the app. Import this once per chart component
// (e.g. `import '../../lib/chartRegistry'`) rather than each one registering
// its own subset, since Chart.js throws at render time for anything unregistered.
import {
  BarController,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip as ChartTooltip,
} from 'chart.js'

ChartJS.register(
  BarController,
  BarElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  ChartTooltip
)
