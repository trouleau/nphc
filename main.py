from utils.cumulants import Cumulants
from itertools import product
from utils.loader import load_data
from scipy.linalg import inv, sqrtm
import tensorflow as tf
import numpy as np


class WarmStart(object):
    def __init__(self, f):
        self.f = f

    def __call__(self):
        print("Call")
        self.f()

def NPHC(cumulants, starting_point, alpha=.5, training_epochs=1000, learning_rate=1e6, optimizer='momentum', \
         stochastic=False, display_step = 100, weightGMM='eye'):

    d = cumulants.dim

    L = tf.placeholder(tf.float32, d, name='L')
    C = tf.placeholder(tf.float32, (d,d), name='C')
    K_c = tf.placeholder(tf.float32, (d,d), name='K_c')
    if stochastic:
        ind_i = tf.placeholder(tf.int32, shape=[1], name='ind_i')
        ind_j = tf.placeholder(tf.int32, shape=[1], name='ind_j')
        ind_ij = tf.placeholder(tf.int32, shape=[1,2], name='ind_ij')
        C_i = tf.gather(C, ind_i)
        C_j = tf.gather(C, ind_j)
        C_ij = tf.gather_nd(C, ind_ij)
        K_c_ij = tf.gather_nd(K_c, ind_ij)

    R = tf.Variable(starting_point, name='R')
    if stochastic:
        R_i = tf.gather(R, ind_i)
        R_j = tf.gather(R, ind_j)

    # Set weight matrices
    cumulants.set_W_2(starting_point, weight=weightGMM)
    cumulants.set_W_3(starting_point, weight=weightGMM)

    if stochastic:
        W_2_ij = tf.gather_nd(cumulants.W_2, ind_ij)
        W_3_ij = tf.gather_nd(cumulants.W_3, ind_ij)

    # Construct model
    activation_3 = tf.matmul(tf.square(R),C,transpose_b=True) + 2.0*tf.matmul(tf.mul(R,C),R,transpose_b=True) - 2.0*tf.matmul(tf.square(R),tf.matmul(tf.diag(L),R,transpose_b=True))
    activation_2 = tf.matmul(R,tf.matmul(tf.diag(L),R,transpose_b=True))

    if stochastic:
        act_3_ij = tf.reduce_sum( tf.mul( C_j, tf.square( R_i) ) + 2.0*tf.mul( tf.mul( R_i, C_i ), R_j ) - 2.0*tf.mul( tf.mul( L, R_j ), tf.square( R_i ) ) )
        act_2_ij = tf.reduce_sum( tf.mul( tf.mul( tf.cast(L,tf.float32), R_i ), R_j ) )

        if weightGMM == 'eye':
            tot_cost = (1-alpha) * tf.reduce_mean( tf.squared_difference( activation_3, K_c ) ) + alpha * tf.reduce_mean( tf.squared_difference( activation_2, C ) )
            cost =  (1-alpha) * tf.reduce_mean( tf.squared_difference( act_3_ij, K_c_ij ) ) + alpha * tf.reduce_mean( tf.squared_difference( act_2_ij, C_ij ) )

        elif weightGMM == 'diag':
            tot_cost = (1-alpha) * tf.reduce_mean( tf.mul( tf.squared_difference( activation_3, K_c ), tf.cast(cumulants.W_3,tf.float32)) ) + alpha * tf.reduce_mean( tf.mul( tf.squared_difference( activation_2, C ) , tf.cast(cumulants.W_2,tf.float32) ) )
            cost =  (1-alpha) * tf.reduce_mean( tf.mul( tf.squared_difference( act_3_ij, K_c_ij ), tf.cast(W_3_ij,tf.float32) ) ) + alpha * tf.reduce_mean( tf.mul( tf.squared_difference( act_2_ij, C_ij ), tf.cast(W_2_ij,tf.float32)) )

        elif weightGMM == 'dense':
            sqrt_W_2 = sqrtm(cumulants.W_2)
            sqrt_W_3 = sqrtm(cumulants.W_3)

            sqrt_W_2_dot_C = tf.matmul( sqrt_W_2, C )
            sqrt_W_3_dot_K_c = tf.matmul( sqrt_W_3, K_c )

            sqrt_W_2_dot_C_ij = tf.gather_nd( sqrt_W_2_dot_C, ind_ij )
            sqrt_W_3_dot_K_c_ij = tf.gather_nd( sqrt_W_3_dot_K_c, ind_ij )

            act_2_ij = tf.gather_nd( tf.matmul( sqrt_W_2, activation_2 ), ind_ij )
            act_3_ij = tf.gather_nd( tf.matmul( sqrt_W_3, activation_3 ), ind_ij )

            tot_cost = (1-alpha) * tf.reduce_mean( tf.mul( activation_3 - K_c , tf.reshape( tf.matmul( tf.cast(cumulants.W_3,tf.float32), tf.reshape(activation_3 - K_c, shape=[d**2,1] ) ), shape=[d,d] ) ) ) \
                       + alpha * tf.reduce_mean( tf.mul( activation_2 - C , tf.reshape( tf.matmul( tf.cast(cumulants.W_2,tf.float32), tf.reshape( activation_2 - C, shape=[d**2,1] ) ), shape=[d,d] ) ) )
            cost =  (1-alpha) * tf.reduce_mean( tf.squared_difference( act_3_ij, sqrt_W_3_dot_K_c_ij )  ) \
                    + alpha * tf.reduce_mean( tf.squared_difference( act_2_ij, sqrt_W_2_dot_C_ij ) )

        tot_cost = tf.cast(tot_cost, tf.float32)
        cost = tf.cast(cost, tf.float32)

    else:

        if weightGMM == 'eye':
            cost =  (1-alpha) * tf.reduce_mean( tf.squared_difference( activation_3, K_c ) ) + alpha * tf.reduce_mean( tf.squared_difference( activation_2, C ) )

        elif weightGMM == 'diag':
            cost =  (1-alpha) * tf.reduce_mean( tf.mul( tf.squared_difference( activation_3, K_c ), tf.cast(cumulants.W_3,tf.float32) ) ) + alpha * tf.reduce_mean( tf.mul( tf.squared_difference( activation_2, C ) , tf.cast(cumulants.W_2,tf.float32) ) )

        elif weightGMM == 'dense':
            cost = (1-alpha) * tf.reduce_mean( tf.mul( activation_3 - K_c , tf.reshape( tf.matmul( tf.cast(cumulants.W_3,tf.float32), tf.reshape(activation_3 - K_c, shape=[d**2,1] ) ), shape=[d,d] ) ) ) \
                    + alpha * tf.reduce_mean( tf.mul( activation_2 - C , tf.reshape( tf.matmul( tf.cast(cumulants.W_2,tf.float32), tf.reshape( activation_2 - C, shape=[d**2,1] ) ), shape=[d,d] ) ) )

        cost = tf.cast(cost, tf.float32)


    if optimizer == 'momentum':
        optimizer = tf.train.MomentumOptimizer(learning_rate, momentum=0.9).minimize(cost)
    elif optimizer == 'adam':
        optimizer = tf.train.AdamOptimizer(learning_rate).minimize(cost)
    elif optimizer == 'adagrad':
        optimizer = tf.train.AdagradOptimizer(learning_rate).minimize(cost)
    elif optimizer == 'rmsprop':
        optimizer = tf.train.RMSPropOptimizer(learning_rate).minimize(cost)
    elif optimizer == 'adadelta':
        optimizer = tf.train.AdadeltaOptimizer(learning_rate).minimize(cost)
    else:
        optimizer = tf.train.GradientDescentOptimizer(learning_rate).minimize(cost)

    # Initialize the variables
    init = tf.initialize_all_variables()

    # Create a summary to monitor cost function
    #tf.scalar_summary('loss', cost)

    # Merge all summaries to a single operator
    #merged_summary_op = tf.merge_all_summaries()

    # Launch the graph
    with tf.Session() as sess:
        sess.run(init)

        # Set logs writer into folder /tmp/tf_cumul
        #summary_writer = tf.train.SummaryWriter('/tmp/tf_cumul', graph=sess.graph)

        # Training cycle
        if stochastic:
            for epoch in range(training_epochs):
                for (i, j) in product(range(d), repeat=2):
                # Fit training using batch data
                    sess.run(optimizer, feed_dict={L: cumulants.L, C: cumulants.C, K_c: cumulants.K_c, ind_i: [i], ind_j: [j], ind_ij: [[i,j]]})
                if epoch % display_step == 0:
                    avg_cost = sess.run(tot_cost, feed_dict={L: cumulants.L, C: cumulants.C, K_c: cumulants.K_c})
                    print("Epoch:", '%04d' % (epoch), "log10(cost)=", "{:.9f}".format(np.log10(avg_cost)))
        else:
            for epoch in range(training_epochs):
                # Fit training using batch data
                sess.run(optimizer, feed_dict={L: cumulants.L, C: cumulants.C, K_c: cumulants.K_c})
                if epoch % display_step == 0:
                    avg_cost = sess.run(cost, feed_dict={L: cumulants.L, C: cumulants.C, K_c: cumulants.K_c})
                    print("Epoch:", '%04d' % (epoch), "log10(cost)=", "{:.9f}".format(np.log10(avg_cost)))
                # Write logs at every iteration
                #summary_str = sess.run(merged_summary_op, feed_dict={L: cumul.L, C: cumul.C, K_c: cumul.K_c})
                #summary_writer.add_summary(summary_str, epoch)

        print("Optimization Finished!")

        return sess.run(R)

'''
Run the command line: tensorboard --logdir=/tmp/tf_cumul
Open http://localhost:6006/ into your web browser
'''

if __name__ == '__main__':

    # Load Cumulants object
    kernel = 'exp_d10'
    mode = 'nonsym_1'
    log10T = 10
    url = 'https://s3-eu-west-1.amazonaws.com/nphc-data/{}_{}_log10T{}_with_params_without_N.pkl.gz'.format(kernel, mode, log10T)
    cumul, Alpha, Beta, Gamma = load_data(url)

    # Params
    learning_rate = 1e7
    training_epochs = 1000
    display_step = 100
    d = cumul.dim

    _, s, _ = np.linalg.svd(cumul.C)
    lbd_max = s[0]
    initial = tf.constant(inv(np.eye(d) - cumul.C / (1.1*lbd_max)).astype(np.float32), shape=[d,d])

    out_1 = NPHC(cumul, initial, alpha=.99, learning_rate=learning_rate)
    print("First step is done!")

    out_2 = NPHC(cumul, out_1, alpha=.5, learning_rate=learning_rate)
    print("Second step is done!")