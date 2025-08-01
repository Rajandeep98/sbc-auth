<template>
  <div data-test="div-payment-view">
    <v-container
      v-if="showLoading"
      data-test="div-payment-view-loading"
    >
      <v-row
        justify="center"
        align="center"
        class="py-12 loading-progressbar flex-column"
      >
        <v-progress-circular
          color="primary"
          :size="80"
          :width="5"
          indeterminate
          class="mt-12"
        />
        <div class="loading-msg">
          {{ showdownloadLoading ? $t('paymentDownloadMsg') : $t('paymentPrepareMsg') }}
        </div>
      </v-row>
    </v-container>
    <div v-else>
      <v-container
        v-if="errorMessage"
        data-test="div-payment-view-error"
      >
        <v-row
          justify="center"
          align="center"
        >
          <SbcSystemError
            v-if="showErrorModal"
            title="Payment Failed"
            primaryButtonTitle="Continue to Filing"
            :description="errorMessage"
            @continue-event="goToUrl(returnUrl)"
          />
          <div
            v-else
            class="mt-12"
          >
            <div class="text-center mb-4">
              <v-icon
                color="error"
                size="30"
              >
                mdi-alert-outline
              </v-icon>
            </div>
            <h4>{{ errorMessage }}</h4>
          </div>
        </v-row>
      </v-container>
      <v-container
        v-if="showOnlineBanking"
        data-test="div-payment-view-container"
        class="view-container"
      >
        <div class="payment-view-content">
          <h1 class="mb-1">
            Make a payment
          </h1>
          <p class="mb-8">
            Please find your balance and payment details below.
          </p>
          <PaymentCard
            :paymentCardData="paymentCardData"
            :showPayWithOnlyCC="showPayWithOnlyCC"
            @complete-online-banking="completeOBPayment"
            @pay-with-credit-card="payNow"
            @download-invoice="downloadInvoice"
          />
        </div>
      </v-container>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator'
import { PaymentTypes, SessionStorageKeys } from '@/util/constants'
import { AccountSettings } from '@/models/account-settings'
import CommonUtils from '@/util/common-util'
import ConfigHelper from '@/util/config-helper'
import { Invoice } from '@/models/invoice'
import { OrgPaymentDetails } from '@/models/Organization'
import PaymentCard from '@/components/pay/PaymentCard.vue'
import PaymentService from '@/services/payment.services'
import SbcSystemError from 'sbc-common-components/src/components/SbcSystemError.vue'
import { mapActions } from 'pinia'
import { useOrgStore } from '@/stores/org'
@Component({
  components: {
    SbcSystemError,
    PaymentCard
  },
  methods: {
    ...mapActions(useOrgStore, [
      'createTransaction',
      'getOrgPayments',
      'getInvoice',
      'updateInvoicePaymentMethodAsCreditCard',
      'downloadOBInvoice'
    ])
  }
})
export default class PaymentView extends Vue {
  @Prop({ default: '' }) paymentId: string
  @Prop({ default: '' }) redirectUrl: string
  readonly createTransaction!: (transactionData) => any
  readonly updateInvoicePaymentMethodAsCreditCard!: (invoicePayload) => any
  readonly downloadOBInvoice!: (paymentId: string) => any
  readonly getOrgPayments!: (orgId: number) => OrgPaymentDetails
  readonly getInvoice!: (invoicePayload) => Invoice
  showLoading: boolean = true
  showdownloadLoading: boolean = false
  showOnlineBanking: boolean = false
  errorMessage: string = ''
  showErrorModal: boolean = false
  returnUrl: string = ''
  paymentCardData: any
  showPayWithOnlyCC: boolean = false
  async mounted () {
    this.showLoading = true
    if (!this.paymentId || !this.redirectUrl) {
      this.showLoading = false
      this.errorMessage = this.$t('payNoParams').toString()
      return
    }
    try {
      const accountSettings = this.getAccountFromSession()
      // user should be signed in and should have account as well
      if (this.isUserSignedIn && !!accountSettings) {
        // get the invoice and check for OB
        try {
          const invoice = await this.getInvoice({ invoiceId: this.paymentId, accountId: accountSettings?.id })
          if (invoice?.paymentMethod === PaymentTypes.ONLINE_BANKING) {
            // get account data to show in the UI
            const paymentDetails: OrgPaymentDetails = await this.getOrgPayments(accountSettings?.id)
            this.paymentCardData = {
              totalBalanceDue: invoice?.total || 0, // to fix credit amount
              payeeName: ConfigHelper.getPaymentPayeeName(),
              cfsAccountId: paymentDetails?.cfsAccount?.cfsAccountNumber || '',
              obCredit: paymentDetails?.obCredit,
              padCredit: paymentDetails?.padCredit,
              paymentId: this.paymentId,
              totalPaid: invoice?.paid || 0
            }
            this.showLoading = false
            this.showOnlineBanking = true
            // if isOnlineBankingAllowed is true, allowed show CC as only payment type
            this.showPayWithOnlyCC = !invoice?.isOnlineBankingAllowed
          }
        } catch (error) {
          // eslint-disable-next-line no-console
          console.error('error in accessing the invoice.Defaulting to CC flow')
        }
      }
      if (!this.showOnlineBanking) {
        await this.doCreateTransaction()
      }
    } catch (error) {
      await this.doHandleError(error)
    }
  }
  // We need this, otherwise we can get redirect Urls with just a single slash.
  get redirectUrlFixed () {
    if (!this.redirectUrl.includes('://')) {
      return this.redirectUrl.replace(':/', '://')
    }
    return this.redirectUrl
  }
  isUserSignedIn (): boolean {
    return !!ConfigHelper.getFromSession('KEYCLOAK_TOKEN')
  }
  getAccountFromSession (): AccountSettings {
    return JSON.parse(ConfigHelper.getFromSession(SessionStorageKeys.CurrentAccount || '{}'))
  }
  goToUrl (url:string) {
    window.location.href = url || this.redirectUrlFixed
  }
  completeOBPayment () {
    this.goToUrl(this.returnUrl)
  }
  async payNow () {
    // patch the transaction
    // redirect for payment
    try {
      const accountSettings = this.getAccountFromSession()
      await this.updateInvoicePaymentMethodAsCreditCard({ paymentId: this.paymentId, accountId: accountSettings?.id })
      await this.doCreateTransaction()
    } catch (error) {
      await this.doHandleError(error)
    }
  }
  async downloadInvoice () {
    // download invoice fot online banking
    this.showLoading = true // to avoid rapid download clicks
    this.showdownloadLoading = true // to avoid rapid download clicks
    this.errorMessage = ''
    try {
      const downloadType = 'application/pdf'
      const response = await this.downloadOBInvoice(this.paymentId)
      const contentDispArr = response?.headers['content-disposition'].split('=')
      const fileName = (contentDispArr.length && contentDispArr[1]) ? contentDispArr[1] : `bcregistry-${this.paymentId}`
      CommonUtils.fileDownload(response.data, fileName, downloadType)
      this.showdownloadLoading = false
      this.showLoading = false
    } catch (error) {
      this.showdownloadLoading = false
      this.showLoading = false
      this.errorMessage = this.$t('downloadFailedMessage').toString()
      // this.showErrorModal = true
    }
  }
  async doCreateTransaction () {
    const transactionDetails = await this.createTransaction({
      paymentId: this.paymentId,
      redirectUrl: this.redirectUrlFixed
    })
    this.showLoading = false
    this.returnUrl = transactionDetails?.paySystemUrl
    this.goToUrl(this.returnUrl)
  }
  async doHandleError (error) {
    this.showLoading = false
    if (error.response.data && ['COMPLETED_PAYMENT', 'INVALID_TRANSACTION'].includes(error.response.data.type)) {
      // Skip PAYBC, take directly to the "clients redirect url", this avoids transaction already done error.
      const isValid = await PaymentService.isValidRedirectUrl(this.redirectUrlFixed)
      if (!isValid) {
        this.errorMessage = this.$t('payFailedMessage').toString()
        throw new Error('Invalid redirect url: ' + this.redirectUrlFixed)
      }
      this.goToUrl(this.redirectUrlFixed)
    } else {
      this.errorMessage = this.$t('payFailedMessage').toString()
      this.showErrorModal = true
    }
  }
}
</script>

<style lang="scss" scoped>
.payment-view-content {
  margin: 0 auto;
  max-width: 48rem;
}
.loading-msg {
  font-weight: 600;
  margin-top: 14px;
}
</style>
