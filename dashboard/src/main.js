import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './styles/variables.css'
import './styles/global.css'

import QButton from './components/QButton.vue'
import QCard from './components/QCard.vue'
import QCheckbox from './components/QCheckbox.vue'
import QCheckboxGroup from './components/QCheckboxGroup.vue'
import QModal from './components/QModal.vue'
import QRadio from './components/QRadio.vue'
import QRadioGroup from './components/QRadioGroup.vue'
import QTabs from './components/QTabs.vue'

const app = createApp(App)
app.use(router)
app.component('QButton', QButton)
app.component('QCard', QCard)
app.component('QCheckbox', QCheckbox)
app.component('QCheckboxGroup', QCheckboxGroup)
app.component('QModal', QModal)
app.component('QRadio', QRadio)
app.component('QRadioGroup', QRadioGroup)
app.component('QTabs', QTabs)
app.mount('#app')
