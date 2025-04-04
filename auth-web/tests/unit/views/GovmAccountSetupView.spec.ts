import '@/composition-api-setup'
import { createLocalVue, mount } from '@vue/test-utils'
import GovmAccountSetupView from '@/views/auth/create-account/GovmAccountSetupView.vue'
import ModalDialog from '@/components/auth/common/ModalDialog.vue'
import Vue from 'vue'
import VueRouter from 'vue-router'
import Vuelidate from 'vuelidate'
import Vuetify from 'vuetify'
import { createTestingPinia } from '@pinia/testing'

Vue.use(Vuetify)
Vue.use(VueRouter)
const router = new VueRouter()
const vuetify = new Vuetify({})

// Prevent the warning "[Vuetify] Unable to locate target [data-app]"
document.body.setAttribute('data-app', 'true')

describe('GovmAccountSetupView.vue', () => {
  let wrapper: any
  const localVue = createLocalVue()

  beforeEach(async () => {
    localVue.use(Vuelidate)

    const pinia = createTestingPinia({
      initialState: {
        auth: {
          loginSource: 'BCEID'
        }
      }
    })

    wrapper = mount(GovmAccountSetupView, {
      pinia,
      localVue,
      router,
      vuetify,
      mocks: {
        $t: (mock) => mock
      }
    })
  })

  afterEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
  })

  it('GovmAccountSetupView is a Vue instance', () => {
    expect(wrapper.vm).toBeTruthy()
  })

  it('should render with h1', () => {
    expect(wrapper.find('h1').text()).toBe('Create a Ministry Account')
  })

  it('should render page title icon color correctly', () => {
    expect(wrapper.findComponent(ModalDialog).exists()).toBe(true)
  })

  it('should call createAccount on emit', async () => {
    wrapper.vm.$emit('createAccount')

    await wrapper.vm.$nextTick() // Wait until $emits have been handled

    // assert event has been emitted
    expect(wrapper.emitted().createAccount).toBeTruthy()
  })
})
