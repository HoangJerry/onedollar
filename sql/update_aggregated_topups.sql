UPDATE `onedollar_onedollaruser` u
       JOIN (SELECT user_id,
                    Sum(amount) AS sum_amount
             FROM   `onedollar_transaction`
             WHERE  transaction_type = 1
             GROUP  BY user_id) t
         ON u.id = t.user_id
SET    u.aggregated_topups = t.sum_amount;
