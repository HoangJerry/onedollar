from django.conf.urls import include, url
import models
import api as api_views

urlpatterns = [
    url(r'^$', api_views.api_root, name='api'),
    url(r'^bets/$', api_views.BetView.as_view(), name='bets-list'),
    url(r'^transactions/$', api_views.TransactionTopup.as_view(), name='transaction-topup'),
    url(r'^users/$', api_views.UserList.as_view(), name='users-list'),
    url(r'^users/signup/$', api_views.UserSignUp.as_view(), name='users-signup'),
    url(r'^users/me/$', api_views.UserProfile.as_view(), name="users-profile"),
    url(r'^users/me/bets/$', api_views.MyBetProductList.as_view(), name="users-me-bets"),
    url(r'^users/me/bets/in_progress/$', api_views.MyInProgressBetProductList.as_view(), name="users-me-bets-in-progress"),
    url(r'^users/me/bets/won/$', api_views.MyWinBetProductList.as_view(), name="users-me-bets-won"),
    url(r'^users/me/bets/failed/$', api_views.MyFailedBetProductList.as_view(), name="users-me-bets-failed"),
    url(r'^users/me/notifications/$', api_views.MyNotification.as_view(), name="users-me-notifications"),
    url(r'^users/me/badges/$', api_views.MyBadges.as_view(), name="users-me-badges"),
    url(r'^users/me/badges/chat/$', api_views.MyChatBadges.as_view(), name="users-me-chat-badges"),
    url(r'^users/me/pushtoken/$', api_views.UserPushToken.as_view(), name='user-pushtoken'),
    url(r'^users/(?P<pk>[0-9]+)/$', api_views.UserDetail.as_view(), name='users-detail'),
    url(r'^users/(?P<pk>[0-9]+|me)/products/$', api_views.UserProductList.as_view(), name='user-product-listing'),
    url(r'^users/(?P<pk>[0-9]+|me)/products/selling/$', api_views.UserSellingProductList.as_view(), name='user-seilling-product-listing'),
    url(r'^users/(?P<pk>[0-9]+|me)/products/sold/$', api_views.UserSoldProductList.as_view(), name='user-sold-product-listing'),
    url(r'^users/(?P<pk>[0-9]+|me)/ratings/$', api_views.UserRatingList.as_view(), name='user-rating-listing'),
    url(r'^users/(?P<pk>[0-9]+)/comments/$', api_views.UserComments.as_view(), name='user-comments'),
    url(r'^users/(?P<pk>[0-9]+)/products/(?P<product>[0-9]+)/comments/$', api_views.UserComments.as_view(), name='user-comments'),
    url(r'^users/(?P<pk>[0-9]+)/products/(?P<product>[0-9]+)/lastread/$', api_views.UserCommentsLastRead.as_view(), name='user-comments-lastread'),
    url(r'^countries/$', api_views.CountryList.as_view(), name='countries-list'),
    url(r'^topuppackages/$', api_views.TopupPackageList.as_view(), name='topuppackages-list'),
    url(r'^categories/$', api_views.CategoryList.as_view(), name='categories-list'),
    url(r'^categories/test/$', api_views.CategoryListTest.as_view(), name='categories-list'),
    url(r'^brands/$', api_views.BrandList.as_view(), name='categories-list'),
    url(r'^products/$', api_views.ProductListCreate.as_view(), name='product-list-create'),
    url(r'^products/(?P<pk>[0-9]+)/$', api_views.ProductRetrieveUpdateDestroy.as_view(), name='product-productretrieveupdatedestroy'),
    url(r'^products/(?P<pk>[0-9]+)/share/$', api_views.ProductShare.as_view(), name='product-share'),
    url(r'^products/(?P<pk>[0-9]+)/bets/$', api_views.ProductBets.as_view(), name='product-bets'),
    url(r'^products/bets/last$', api_views.Product10BetsLast.as_view(), name='product-bets'),
    url(r'^products/(?P<pk>[0-9]+)/comments/$', api_views.ProductComments.as_view(), name='product-comments'),
    url(r'^products/(?P<pk>[0-9]+)/lastread/$', api_views.ProductCommentsLastRead.as_view(), name='product-comments-lastread'),
    url(r'^productphotos/(?P<pk>[0-9]+)/$', api_views.ProductPhotoDelete.as_view(), name='productphoto-destroy'),
    url(r'^password/forget/$', api_views.ForgetPassword.as_view(), name='password-forget'),
    url(r'^email/verify/$', api_views.SendVerificationEmail.as_view(), name='email-verify'),
    url(r'^email/verify/check/$', api_views.CheckVerificationEmail, name='email-verify'),
    url(r'^rating/$', api_views.RatingView.as_view(), name="rating"),
    url(r'^reporttypes/user/$', api_views.UserReportingTypeList.as_view(), name="user-report-types"),
    url(r'^reporttypes/product/$', api_views.ProductReportingTypeList.as_view(), name="product-report-types"),
    url(r'^report/user/$', api_views.ReportUserCreate.as_view(), name="user-report"),
    url(r'^report/product/$', api_views.ReportProductCreate.as_view(), name="product-report"),
    url(r'^claim/$', api_views.Claim.as_view(), name="claim"),
    url(r'^backend/stats/$', api_views.BackendStats.as_view(), name="backend-stats"),
    url(r'^settings/$', api_views.Settings.as_view(), name="settings"),
    url(r'^referrer/(?P<referral_code>[a-z0-9-]+)/$', api_views.UserReferrer.as_view(), name='users-referrer'),

    # url(r'^users/(?P<pk>[0-9]+)/luckyticket/$', api_views.UserReferrer.as_view(), name='users-referrer'),


    url(r'^users/(?P<pk>[0-9]+)/lucky$', api_views.UserLuckyNumber.as_view(), name='user-lucky'),

    # Login and logout views for the browsable API
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),

    # return other-users-also-bet-on products
    url(r'^products/(?P<pk>[0-9]+)/dollars/(?P<prize>[0-9]+)/$', api_views.GetDollarForProduct.as_view(), name='getdollarforproduct'),
    url(r'^products/(?P<pk>[0-9]+)/other-users-bet-on/$', api_views.ProductsOtherUserBetOn.as_view(), name='other-users-bet-on'),
    url(r'^catshowhide/$', api_views.CatShowHide.as_view(), name='catshowhide'),

    # merchants
    url(r'^merchants/signup/$', api_views.MerchantsSignUp.as_view(), name='merchants-signup'),

    # mini cat
    url(r'^users/me/cat_spin/$', api_views.CatSpin.as_view(), name='cat_spin'),
    url(r'^users/me/cat_spin/uncage/(?P<pk>[0-9]+)/$', api_views.CatSpinUncage.as_view(), name='cat_uncage'),
    url(r'^users/me/cat_spin/spin/(?P<pk>[0-9]+)/$', api_views.GetCoins.as_view(), name='spin'),
    url(r'^users/me/cat_spin/claim/$', api_views.CatClaim.as_view(), name='spin'),
    url(r'^users/me/cat_spin/stopdiscount/$', api_views.StopDiscount.as_view(), name='spin'),


    url(r'^users/me/getnoti/$', api_views.GetNoti.as_view(), name='getnoti'),
    # url(r'^check/$', api_views.pns_spin_cat_uncage, name='check'),


]
