<template>
  <v-container
    class="view-container"
    data-test="div-account-setup-success-container"
  >
    <v-row justify="center">
      <v-col
        cols="12"
        sm="6"
        class="text-center"
      >
        <v-icon
          size="48"
          color="primary"
          class="mb-6"
        >
          mdi-clock-outline
        </v-icon>
        <h1>{{ $t('govmAccountCreationSuccessTitle') }}</h1>
        <p class="mt-8 mb-10">
          {{ $t('govmAAccountCreationSuccessSubtext') }}
        </p>
        <div class="btns">
          <v-btn
            large
            color="primary"
            class="action-btn font-weight-bold"
            data-test="btn-goto-home"
            @click="goTo('home')"
          >
            Home
          </v-btn>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">

import { Component, Mixins } from 'vue-property-decorator'
import AccountMixin from '@/components/auth/mixins/AccountMixin.vue'
import { Organization } from '@/models/Organization'
import { Pages } from '@/util/constants'
import { mapState } from 'pinia'
import { useOrgStore } from '@/stores/org'

@Component({
  computed: {
    ...mapState(useOrgStore, ['currentOrganization'])
  }
})
export default class AccountCreationSuccessView extends Mixins(AccountMixin) {
  protected readonly currentOrganization!: Organization

  goTo (page) {
    switch (page) {
      case 'home': this.$router.push('/')
        break
      case 'team-members': this.$router.push(`/${Pages.MAIN}/${this.currentOrganization.id}/settings/team-members`)
        break
      case 'setup-team': this.$router.push(`account-login-options-info`)
        break
    }
  }
}
</script>

<style lang="scss" scoped>
  .action-btn {
    width: 8rem;
  }
</style>
