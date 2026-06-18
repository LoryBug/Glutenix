import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import IngredientsView from '../views/IngredientsView.vue'
import BlendsView from '../views/BlendsView.vue'
import SimulationView from '../views/SimulationView.vue'
import SimulationHistoryView from '../views/SimulationHistoryView.vue'
import SweepView from '../views/SweepView.vue'
import PredictionView from '../views/PredictionView.vue'
import OptimizationView from '../views/OptimizationView.vue'

const routes = [
  { path: '/', name: 'Dashboard', component: DashboardView },
  { path: '/ingredients', name: 'Ingredients', component: IngredientsView },
  { path: '/blends', name: 'Blends', component: BlendsView },
  { path: '/simulate', name: 'Simulate', component: SimulationView },
  { path: '/simulate/history', name: 'SimHistory', component: SimulationHistoryView },
  { path: '/simulate/sweep', name: 'Sweep', component: SweepView },
  { path: '/predict', name: 'Predict', component: PredictionView },
  { path: '/optimize', name: 'Optimize', component: OptimizationView },
]

export default createRouter({ history: createWebHistory(), routes })
